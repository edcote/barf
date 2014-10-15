#!/usr/bin/env python
"""
BARF - Build and Run Flow
Copyright (c) 2014 Edmond Cote <edmond.cote@gmail.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import argparse
import logging
import os
import re
import subprocess
import sys
import time
import traceback
import yaml


class Barf(object):
    """ Build and Run Flow """


    def __init__(self):
        """ Creates object of type Barf """
        self.setup_argparse()
        self.setup_logger()
        self.check_env_setup()

    def setup_argparse(self):
        """ Setup argument parser """
        # First level of argument parsing
        self.barf_parser = argparse.ArgumentParser(description=
                                                   'Build and Run Flow 0.5',
                                                   add_help=False)

        self.barf_parser.add_argument('-f','--file', type=argparse.FileType('r'),
                            help='BARF script to execute', required=True)
        self.barf_parser.add_argument('-v','--verbose',
                            help='Verbose output',action='store_true')
        self.barf_args, self.args_list = self.barf_parser.parse_known_args()


    def get_brf_file(self):
        """ Returns full path of BARF script file """
        return self.barf_args.file.name

    def setup_logger(self):
        """ Setup logger object """ 
        self.logger = logging.getLogger('BARF')
        if self.barf_args.verbose:
            logging.basicConfig(level=logging.INFO)

    def check_env_setup(self):
        """ Checks environment setup """
        if not os.environ.has_key("WS"):
            raise Exception('$WS not set')
        self.logger.info('$WS='+os.environ.get('WS'))

        if not os.environ.has_key("WSTMP"):
            raise Exception('$WSTMP not set')
        self.logger.info('$WSTMP='+os.environ.get('WSTMP'))

    def set_top_comp(self, top_comp):
        """ Sets name of top node """
        self.logger.info('top_comp='+top_comp)
        self.top_comp = top_comp

    def get_top_comp(self):
        """ Gets name of top component """
        if not self.top_comp:
            raise RuntimeError('top node must be set')
        return self.top_comp

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

    def load_comps(self, top_comp=''):
        """ Load components from yaml files """
        self.logger.info("load_comps {}".format(top_comp))

        if top_comp != '':
            self.set_top_comp(top_comp)

        if not self.top_comp:
            raise RuntimeError('top node must be set')

        self.logger.info('top_comp='+self.top_comp)

        self.comp = {}

        for root, dirs, files in os.walk(os.environ.get('WS')):
            for f in files:
                if f == "comp.yml":
                    full_path = os.path.join(root, f)
                    self.logger.info('comp_path='+full_path)

                    stream = yaml.load(open(full_path))

                    # http://www.pythonforbeginners.com#/basics/list-comprehensions-in-python
                    stream['files'] = [((root+'/'+x) if x[0] != "$" else x) for x in stream['files'] ]
                    self.logger.info(stream)

                    name = stream['name']
                    self.logger.info('comp_name='+name)
                    self.comp[name] = {}
                    self.comp[name]['files'] = stream['files']
                    self.comp[name]['options'] = stream['options'] 
                    self.comp[name]['requires'] = stream['requires']
                    self.comp[name]['visited'] = 0

        self.flist_obj = []

        if not self.top_comp in self.comp:
            raise RuntimeError('top node not found in component tree')

        self.post_order(self.comp[self.top_comp])

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

    def guess_top_module(self):
        """ Guess the component's top module """
        top_module = ''
        f = open(self.flist_obj[-1]['files'][0])  # return last element in list
        for line in f.readlines():
            m = re.search('module\s+(\w+)\s*;', line)
            if m:
                top_module = m.group(1)
                break
        if top_module == '':
            raise Exception('Unable to guess top module')
        f.close()
        return top_module


class Job(object):
    """ Base class for job object """

    def __init__(self, name):
        self.name = name
        self.wstmp = os.environ.get('WSTMP')
        self.tstamp = ''

    def get_wdir(self):
        if self.tstamp:
            wdir = "{}/{}/{}".format(self.wstmp, self.name, self.tstamp)
        else:
            wdir = "{}/{}".format(self.wstmp, self.name)
        if not os.path.exists(wdir):
            os.makedirs(wdir)
        if self.tstamp:
            dst = wdir + '/../latest'
            if os.path.exists(dst):
                os.unlink(dst)
            os.symlink(wdir, wdir + '/../latest')
        return wdir

    def set_tstamp(self):
        self.tstamp = time.strftime("%m%d_%H%M%S")

    def exec_cmd(self,cmd):
        """ Execute shell command """
        p = subprocess.Popen('cd {0} && {1}'.format(self.get_wdir(),
                                                    cmd),
                                                    stdout=subprocess.PIPE,
                                                    shell=True)
        (stdout, stderr) = p.communicate()

        print('#'*80)
        print('# Command: {0}'.format(cmd))
        print('# Working dir: {0}'.format(self.get_wdir()))
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


if __name__ == '__main__':
    try:
        barf = Barf()
        execfile(barf.get_brf_file())
        sys.exit(0)
    except Exception, err:
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)
