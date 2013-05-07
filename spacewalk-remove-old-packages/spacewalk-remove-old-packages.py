#!/usr/bin/python
#
# Deletes older packages from a channel and from Spacewalk
# Author: Martin Zehetmayer <angrox@idle.at>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
# ---------------
#
# This script deletes all old packages from one channel and - if wanted - 
# deletes the files from storage as well. 
#
# BE CAREFUL WITH THIS SCRIPT! TEST IT BEFORE USING IT IN PRODUCTION!
# I must point again at the "WITHOUT ANY WARRANTY" line :-)
#
# usage: spacewalk-remove-old-packages.py [options]
# 
# options:
#   -h, --help            show this help message and exit
#   -s SPW_SERVER, --spw-server=SPW_SERVER
#                         Spacewalk Server
#   -u SPW_USER, --spw-user=SPW_USER
#                         Spacewalk User
#   -p SPW_PASS, --spw-pass=SPW_PASS
#                         Spacewalk Password
#   -f CFG_FILE, --config-file=CFG_FILE
#                         Config file for servers, users, passwords
#   -c CHANNEL, --channel=CHANNEL
#                         Channel Label: ie."myown-rhel-6-x86_64"
#   -w, --without_channels
#                         Delete packages without channel. Overwrites the
#                         channel option
#   -n, --dryrun          No Change is actually made, only print what would be
#                         done

#
#
# The configuration file must be parseable bei ConfigParser:
# Example: 
#
# [Spacewalk]
# spw_server = spacewalk.example.com
# spw_user   = api_user_1
# spw_pass   = api_password_1

import xmlrpclib
import datetime
import ConfigParser
import sys
import os

from subprocess import *
from optparse import OptionParser


def parse_args():
    parser = OptionParser()
    parser.add_option("-s", "--spw-server", type="string", dest="spw_server",
            help="Spacewalk Server")
    parser.add_option("-u", "--spw-user", type="string", dest="spw_user",
            help="Spacewalk User")
    parser.add_option("-p", "--spw-pass", type="string", dest="spw_pass",
            help="Spacewalk Password")
    parser.add_option("-f", "--config-file", type="string", dest="cfg_file",
            help="Config file for servers, users, passwords")
    parser.add_option("-c", "--channel", type="string", dest="channel",
            help="Channel Label: ie.\"lhm-rhel-6-x86_64\"")
    parser.add_option("-w", "--without_channels", action="store_true", dest="wo_channel",
            help="Delete packages without channel. Overwrites the channel option")
    parser.add_option("-n", "--dryrun", action="store_true", dest="dryrun",
            help="No Change is actually made, only print what would be done")
    (options,args) = parser.parse_args()
    return options


def cmp_dictarray(pkgs, id):
    for pkg in pkgs:
        for (key,val) in pkg.iteritems():
            if val == id:
                return True
    return False



def main():

    # Get the options
    options = parse_args()
    # read the config
    if options.cfg_file:
        config = ConfigParser.ConfigParser()
        config.read (options.cfg_file)
        if options.spw_server is None:
            options.spw_server = config.get ('Spacewalk', 'spw_server')
        if options.spw_user is None:
            options.spw_user = config.get ('Spacewalk', 'spw_user')
        if options.spw_pass is None:
            options.spw_pass = config.get ('Spacewalk', 'spw_pass')

    if options.channel is None and options.wo_channel is None:
        print "Channel not given, aborting"
        sys.exit(2)

    spacewalk = xmlrpclib.Server("https://%s/rpc/api" % options.spw_server, verbose=0)
    spacekey = spacewalk.auth.login(options.spw_user, options.spw_pass)
   
    to_delete=[]
    to_delete_ids=[]
    # get all packages
    if options.wo_channel is None: 
        print "Getting all packages"
        allpkgs = spacewalk.channel.software.listAllPackages(spacekey, options.channel)
        print " - Amount: %d" % len(allpkgs)
        # get newest packages
        print "Getting newest packages"
        newpkgs = spacewalk.channel.software.listLatestPackages(spacekey, options.channel)
        print " - Amount: %d" % len(newpkgs)
        for pkg in allpkgs:
            if not cmp_dictarray(newpkgs, pkg['id']):
                print "Marked:  %s-%s-%s (id %s)" % (pkg['name'], pkg['version'], pkg['release'], pkg['id'])
                to_delete.append(pkg)
                to_delete_ids.append(pkg['id'])
        print "Packages to remove: %s" % len(to_delete)
        print "Removing packages from channel..."
    else:
        print "Getting all packages without channel"
        lostpkgs = spacewalk.channel.software.listPackagesWithoutChannel(spacekey)
        to_delete=lostpkgs

    if len(to_delete) > 0:
        if options.dryrun is None:
            if options.wo_channel is None:
                print "Remove packages from Channel %s" % options.channel
                ret = spacewalk.channel.software.removePackages(spacekey, options.channel, to_delete_ids)
        elif options.wo_channel is None:
            print "Dryrun: Remove the packages from channel %s" % options.channel
        print "Deleting packages from spacewalk (if packages could not be removed they are maybe in another channel too)"  
        for pkg in to_delete:
            if options.dryrun is not None:
                print "Dryrun: - Delete package %s-%s-%s (ID: %s)" % (pkg['name'], pkg['version'], pkg['release'], pkg['id'])
            else:
                print "Deleting package %s-%s-%s (ID: %s)" % (pkg['name'], pkg['version'], pkg['release'],pkg['id'])
                try: 
                    ret = spacewalk.packages.removePackage(spacekey, pkg['id'])
                except: 
                    print "  - Could not delete package from spacewalk"
                if ret != 1:
                    print " - Could not delete package %s-%s-%s (ID: %s)" % (pkg['name'], pkg['version'], pkg['release'],pkg['id'])
            
    


## MAIN
if __name__ == "__main__":
    main() 
