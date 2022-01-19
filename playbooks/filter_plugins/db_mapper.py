#!/usr/bin/python
import re

class FilterModule(object):
    def filters(self):
        return {'war_to_db': self.war_to_db}


    def war_to_db(self, warfile, dmap):

        pre_db = 'https://databases.dhis2.org/sierra-leone/'
        post_db = '/dhis2-db-sierra-leone.sql.gz'

        db_file = ""

        if warfile in dmap and dmap[warfile] != '':
            db_file = dmap[warfile]
        else:
            if re.search("2\.[0-9][0-9]\.[0-9]+", warfile):
                if re.search("2\.[0-9][0-9]\.[0-9]+-rc", warfile):
                    ver = re.search("2\.[0-9][0-9]\.[0-9]+", warfile).group(0)
                    patch = ver.split('.')[-1]
                    if int(patch) > 0:
                        patch = int(patch) - 1
                    db_file = pre_db+ver[:4]+'.'+str(patch)+post_db
                else:
                    ver = re.search("2\.[0-9][0-9]\.[0-9]+", warfile).group(0)
                    db_file = pre_db+ver+post_db
            else:
                if re.search("2\.[0-9][0-9]", warfile):
                    ver = re.search("2\.[0-9][0-9]", warfile).group(0)
                else:
                    ver = "dev"
                db_file = pre_db+ver+post_db
        return db_file

    def get_war_link(self, reference):

        prefix = 'https://releases.dhis2.org/'

        # if the reference starts with `http` assume it is full link and return unchanged

        # else if the reference ends in `.war` assume it is full path and append to prefix

        # else if the reference contains full patch `2.xx.y` then
            # generate the stable link (keep any prefix like `-rc` or `-EMBARGOED`)

        # else determine if it is dev or canary
        
