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

import argparse
import logging
import os
import subprocess
import sys
import traceback
import yaml

class Barf(object):
    """ Build and Run Flow """

    def __init__(self,top_node=''):
        """ Creates object of type Barf """    
        self.logger = logging.getLogger('BARF')
        if top_node != '':
            self.set_top_node(top_node)
            self.load_comps()

    def set_top_node(self, top_node):
        self.top_node = top_node

    def post_order(self, node):
        """ Recursive post order tree traversal """
        self.logger.info('node='+str(node))

        if not node:
            raise RuntimeError(node+' is not defined')

        for child_name in node['requires']:
            child_node = self.comp[child_name]
            self.post_order(child_node)
        if node['visited'] == 0:
            self.flist_obj.append(node)
            node['visited'] = 1

    def load_comps(self):
        """ Load components from yaml files """
        if not self.top_node:
            raise RuntimeError('top node not set by user')

        self.logger.info('top_node='+self.top_node)

        self.comp = {}

        for root,dirs,files in os.walk(os.environ.get('WS')):
            for f in files:
                if f == "comp.yml":
                    full_path = os.path.join(root, f)
                    self.logger.info('node_path='+full_path)

                    stream = yaml.load(open(full_path))

                    # http://www.pythonforbeginners.com#/basics/list-comprehensions-in-python
                    stream['files'] = [((root+'/'+x) if x[0] != "$" else x) for x in stream['files'] ]
                    self.logger.info(stream)

                    name = stream['name']
                    self.logger.info('node_name='+name)
                    self.comp[name] = {}
                    self.comp[name]['files'] = stream['files']
                    self.comp[name]['options'] = stream['options'] 
                    self.comp[name]['requires'] = stream['requires']
                    self.comp[name]['visited'] = 0

        self.flist_obj = []

        if not self.top_node in self.comp:
            raise RuntimeError('top node not found')

        self.post_order(self.comp[self.top_node])

    def get_flist(self):
        """ Returns list of files """
        files = []
        for obj in self.flist_obj:
            files +=  obj['files']
        return ' '.join(files)

    def get_vopts(self):
        """ Returns list of Verilog options """ 
        options = []
        for obj in self.flist_obj:
            options +=  obj['options']
        return ' '.join(options)

class Job(object):
    """ Base class for job object """

    def exec_cmd(self,cmd,wdir=os.environ.get('WSTMP')):
        """ Execute shell command """
        p = subprocess.Popen('cd {0} && {1}'.format(wdir,cmd),
                                                    stdout=subprocess.PIPE,
                                                    shell=True)
        (stdout, stderr) = p.communicate()

        print('#'*80)
        print('# Command:')
        print('# {0}'.format(cmd))
        print('# Working dir: {0}'.format(wdir))
        print('#'*80 + '\n\n')
        if stdout:
            print(stdout)
        print('\n')

        if stderr:
            sys.stderr.write(stderr)

        if p.returncode != 0: raise Exception("Command {0} failed ".format(cmd))

        return (stdout, stderr)

class CleanTmp(Job):
    def execute(self,lib_name='work'):
        wstmp = os.environ.get('WSTMP')
        if os.path.isdir(wstmp):
            self.exec_cmd('rm -rf {0}/*'.format(wstmp))
        self.exec_cmd('mkdir -p {0}'.format(wstmp),wdir='.')

# http://doughellmann.com/2009/06/19/python-exception-handling-techniques.html
def main():
    if not os.environ.has_key("WS"):
        raise Exception('$WS not set')

    if not os.environ.has_key("WSTMP"):
        raise Exception('$WSTMP not set')

    parser = argparse.ArgumentParser(description='Build and Run Flow 0.3')
    parser.add_argument('-f','--file',
                        help='BARF script to execute',required=True)
    parser.add_argument('-t','--top',
                        help='Name of top component')
    parser.add_argument('-v','--verbose',
                        help='Verbose output',action='store_true')
    parser.parse_args()

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    execfile(args.file)

if __name__ == '__main__':
    try:
        main()
        sys.exit(0)
    except Exception, err:
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)
