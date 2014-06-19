#!/usr/bin/env python

"""
The MIT License (MIT)

Copyright (c) 2014 Edmond Cote <edmond.cote@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in
    all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
    THE
    SOFTWARE.
""" 

import code
import os
import subprocess
import sys
import yaml

class Barf(object):
    """ Build and Run Flow """

    def post_order(self, node):
        """ Recursive post order tree traversal """
        if not node:
            return
        for child_name in node['requires']:
            child_node = self.comp[child_name]
            self.post_order(child_node)
        if node['visited'] == 0:
            self.flist_obj.append(node)
            node['visited'] = 1

    def load_comps(self, top_node):
        """ Load components from yaml files """
        self.comp = {}

        for root,dirs,files in os.walk(os.environ.get('WS')):
            for file in files:
                if file == "comp.yml":
                    full_path = os.path.join(root, file)
                    stream = yaml.load(open(full_path))

                    stream['files'] = [ root+'/'+x for x in stream['files'] ]

                    name = stream['name']
                    self.comp[name] = {}
                    self.comp[name]['files'] = stream['files']
                    self.comp[name]['options'] = stream['options'] 
                    self.comp[name]['requires'] = stream['requires']
                    self.comp[name]['visited'] = 0

        self.flist_obj = []        
        self.post_order(self.comp[top_node])

class Job(object):
    """ Base class for job object """

    def exec_cmd(self,cmd,wdir=os.environ.get('WSTMP')):
        """ Execute shell command """
        p = subprocess.Popen('cd {0} && {1}'.format(wdir,cmd),
                                                    stdout=subprocess.PIPE,shell=True)
        (stdout, stderr) = p.communicate()

        print('#' * 80)
        print('#')
        print('# Command: {0}'.format(cmd))
        print('# Working dir: {0}'.format(wdir))
        print('#')
        print('#' * 80 + '\n')
        if stdout:
            print(stdout)
        print('\n')

        if stderr:
            sys.stderr.write(stderr)

        if p.returncode != 0: raise Exception("Command {0} failed ".format(cmd))

        return (stdout, stderr)

    def cyg_to_win_path(self,cyg_path):
        """ Convert cygwin path to windows path """
        p = subprocess.Popen('cygpath -w '+cyg_path,stdout=subprocess.PIPE,shell=True)
        return '"'+p.communicate()[0].rstrip()+'"'

class GenFlist(Job):
    def execute(self,flist_obj):
        pass

class CleanTmp(Job):
    def execute(self,lib_name='work'):
        wstmp = os.environ.get('WSTMP')
        if os.path.isdir(wstmp):
            self.exec_cmd('rm -rf {0}/*'.format(wstmp))
        self.exec_cmd('mkdir -p {0}'.format(wstmp),wdir='.')

class RunVlib(Job):
    def execute(self,lib_name='work'):
        self.exec_cmd('vlib {0}'.format(lib_name))

class RunVlog(Job):
    def execute(self,flist_obj):
        files = []
        for obj in flist_obj:
            files +=  obj['files']
        files = [ self.cyg_to_win_path(x) for x in files ]

        options = []
        for obj in flist_obj:
            options +=  obj['options']

        self.exec_cmd('vlog -sv {0} {1}'.format(' '.join(files),
                                                ' '.join(options)))

if __name__ == "__main__":
    import argparse
    import barf

    # Print banner
    print('''.______        ___      .______       _______ 
|   _  \      /   \     |   _  \     |  ____|
|  |_)  |    /  ^  \    |  |_)  |    |  |__
|   _  <    /  /_\  \   |      /     |   __|
|  |_)  |  /  _____  \  |  |\  \----.|  |
|______/  /__/     \__\ | _| `._____||__|

       BARF - Build and Run Flow 0.1
''')

    parser = argparse.ArgumentParser(description='Build and Run Flow 0.1')
    parser.add_argument('-f','--file',
                        help='BARF script to execute',required=True)
    parser.parse_args()

    execfile(parser.parse_args().file)

