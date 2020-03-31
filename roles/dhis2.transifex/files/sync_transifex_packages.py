#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copyright (c) 2020, University of Oslo
All rights reserved.


@author: philld
"""

import requests
import json
import argparse
import os
import glob
import sys

parser = argparse.ArgumentParser(description='Pull translations from dhis2 API and create files for transifex.')
parser.add_argument('-u','--user', action="store", help='dhis2 user', required=True)
parser.add_argument('-p','--password', action="store", help='dhis2 password', required=True)
parser.add_argument('-s','--server', action="store", help='dhis2 server instance', required=True)  # e.g. https://whom.dhis2.org/phil_dev
parser.add_argument('-k','--package', action="store", help='dhis2 metadata package name', required=True) # e.g. "COVID19_AGG/COVID19_agg"
parser.add_argument('-j','--project', action="store", help='dhis2 project name', required=True) # e.g. meta-who-packages
parser.add_argument('-t','--tx_token', action="store", help='transifex api token', required=True)
args = parser.parse_args()

localisation_dir = "i18n"
locale_file_pattern = localisation_dir + "/{p}_{l}.json"
source_file_pattern = localisation_dir + "/{p}.json"

locale_file_glob_pattern = localisation_dir + "/{p}_*.json"
locale_file_prefix = localisation_dir + "/{p}_"

# Transifex
# project_slug='meta-who-packages'
project_slug=args.project
pack=args.package
tx_i18n_type='KEYVALUEJSON'
tx_mode='onlytranslated'
tx_langs_api='https://www.transifex.com/api/2/project/{s}/resource/{r}/?details'
tx_stats_api='https://www.transifex.com/api/2/project/{s}/resource/{r}/stats/{l}'
tx_translations_api='https://www.transifex.com/api/2/project/{s}/resource/{r}/translation/{l}/?mode={m}&file'
tx_resources_api='https://www.transifex.com/api/2/project/{s}/resources/'
tx_content_api='https://www.transifex.com/api/2/project/{s}/resource/{r}/content'
tx_translations_update_api='https://www.transifex.com/api/2/project/{s}/resource/{r}/translation/{l}'
metadata_extract_config_root="https://raw.githubusercontent.com/dhis2/metadata-package-development/work-in-progress/metadata/"
metadata_extract_config_suffix="_export_conf.json"
excluded_objects=["organisationUnits","users","organisationUnit","user"]


AUTH=(args.user, args.password)
TX_AUTH=('api',args.tx_token)

fromDHIS2={}
package_ids = set()
resource_slug=""

def metadata_to_json():

    print("Pulling translatable metadata from", args.server, "...")

    # first we will find out which fields are translatable, and store them with the resource.
    translatable_fields={}
    dhis2_schemas = requests.get(args.server+"/api/schemas.json",auth=AUTH)
    if dhis2_schemas.status_code == 401:
        print(AUTH)
        sys.exit("DHIS2 user not authorised! Aborting transifex synchronisation.")

    for schema in dhis2_schemas.json()["schemas"]:
        # print(schema['name'])
        if schema['translatable'] == True and 'apiEndpoint' in schema:
            # print("\t",schema['name'])
            # print("\t\t",schema['href'])
            fields= [t for t in schema["properties"] if 'translationKey' in t]
            mapped_fields={}
            for f in fields:
                mapped_fields[f['fieldName']]=f['translationKey']
                # print(schema['name']+"."+f['fieldName'],"==>",f['translationKey'])
            translatable_fields[schema['collectionName']]=mapped_fields

    # print(json.dumps(translatable_fields, indent=2, separators=(',', ': ')))


    locales={}
    locales["source"]={}
    for resource in translatable_fields:
        if resource not in excluded_objects:
            # print(resource, translatable_fields[resource])
            collection = (requests.get(args.server+"/api/"+resource+".json"+"?fields=:all&paging=false",auth=AUTH)).json()[resource]
            for element in collection:
                if element['id'] in package_ids:
                    # print(element['id'])
                    translations= element["translations"]
                    if translations != []:
                        if resource not in fromDHIS2:
                                fromDHIS2[resource] = {}
                        if element['id'] not in fromDHIS2[resource]:
                            fromDHIS2[resource][element['id']] = {}
                            fromDHIS2[resource][element['id']]['translations'] = translations
                        else:
                            fromDHIS2[resource][element['id']]['translations'] += translations
                        # print(resource, element['id'], translations)

                    for transField in translatable_fields[resource]:
                        transFieldKey = translatable_fields[resource][transField]

                        # we can only create translation strings in transifex when a source base field has a value
                        if transField in element:
                            matching_translations=[m for m in translations if m['property'] == transFieldKey]
                            # print( transField, element[transField])
                            if resource not in locales['source']:
                                locales['source'][resource] = {}
                            if element['id'] not in locales['source'][resource]:
                                locales['source'][resource][element['id']] = {}
                            locales['source'][resource][element['id']][transFieldKey] = element[transField]

                            for m in matching_translations:
                                if m['locale'] not in locales:
                                    locales[m['locale']]={}
                                if resource not in locales[m['locale']]:
                                    locales[m['locale']][resource] = {}
                                if element['id'] not in locales[m['locale']][resource]:
                                    locales[m['locale']][resource][element['id']] = {}
                                locales[m['locale']][resource][element['id']][transFieldKey] = m['value']
                        else:
                            # check and warn if we have translations with no base string
                            matching_translations=[m for m in translations if m['property'] == transFieldKey]
                            for m in matching_translations:
                                print("WARNING: Translation without base string for",resource,">",element['id'],":", m)

    # mfile= open("fromMeta.json",'w')
    # mfile.write(json.dumps(fromDHIS2, sort_keys=True, indent=2, separators=(',', ': ')))
    # mfile.close()

    for locale in locales:
        locale_filename = locale_file_pattern.format(p=resource_slug, l=locale)
        if locale == "source":
            locale_filename = source_file_pattern.format(p=resource_slug)
        # print("file:",locale_filename)
        # print("locale:",locale)
        os.makedirs(os.path.dirname(locale_filename), exist_ok=True)
        jsonfile= open(locale_filename,'w')
        jsonfile.write(json.dumps(locales[locale] , sort_keys=True, indent=2, separators=(',', ': ')))
        jsonfile.close()


def merge_translations(dict1, dict2):
    """ Recursively merges dict2 into dict1 """
    if not isinstance(dict1, dict) or not isinstance(dict2, dict):
        return dict1 + dict2
    for k in dict2:
        if k in dict1:
            dict1[k] = merge_translations(dict1[k], dict2[k])
        else:
            dict1[k] = dict2[k]
    return dict1


def minimise_translations(in_trans, out_trans):
    """ Keeps only altered sets of translations """

    if isinstance(out_trans, list):
        if len(out_trans) != len(in_trans):
            return out_trans.copy()

        i_match = 0
        for o in out_trans:
            s_out = json.dumps(o , sort_keys=True)
            for i in in_trans:
                s_in = json.dumps(i , sort_keys=True)
                if s_in == s_out:
                    i_match += 1
        if len(out_trans) != i_match:
            return out_trans.copy()

        return []

    delta = {}
    for k in out_trans:
        if k in in_trans:
            delta[k] = minimise_translations(in_trans[k], out_trans[k])
            if len(delta[k]) == 0:
                delta.pop(k,None)
        else:
            return {k : out_trans[k]}

    return delta

    # return delta


def json_to_transifex():

    print("Pushing source strings to transifex...")

    # get a list of resources for the project
    tx_resources = []
    urlr = tx_resources_api.format(s=project_slug)
    response = requests.get(urlr, auth=TX_AUTH)
    if response.status_code == requests.codes['OK']:
        res = (x['slug'] for x in response.json())
        for resource_s in res:
            tx_resources.append(resource_s)

    path_to_file=source_file_pattern.format(p=resource_slug)

    # check if our resource exists
    if resource_slug in tx_resources:
        # If it does - update it
        url = tx_content_api.format(s=project_slug, r=resource_slug)
        content = open(path_to_file, 'r').read()
        data = {'content': content}
        r = requests.put(
             url, data=json.dumps(data), auth=TX_AUTH, headers={'content-type': 'application/json'},
        )
        print(r.status_code,": PUT ",url)
    else:
        # if it doesn't - create it
        print("Resource does not exist. Creating...")
        url = tx_resources_api.format(s=project_slug)
        data = {
            'name': resource_slug,
            'slug': resource_slug,
            'i18n_type': tx_i18n_type,
            'content': open(path_to_file, 'r').read()
        }
        r = requests.post(
            url,
            data=json.dumps(data),
            auth=TX_AUTH,
            headers={'content-type': 'application/json'}
        )
        print(r.status_code,": POST ",url)


def find_ids(key, var, parent=""):
  if hasattr(var,'items'):
        for k, v in var.items():
            if k == key:
                yield v
            if isinstance(v, dict):
                for result in find_ids(key, v, k):
                    yield result
            elif isinstance(v, list):
                for d in v:
                    for result in find_ids(key, d, k):
                        yield result

def find_keys(key, var, parent=""):
  if hasattr(var,'items'):
        for k, v in var.items():
            if k == key:
                # print("==== parent:", parent)
                # if isinstance(v, dict):
                #     print(var)
                #     print(key,k,v)
                if key == "id" and parent != "" and v not in package_ids:
                    myURL=args.server+"/api/"+parent+"/"+v
                    # print("myURL", myURL)
                    recurse_objects(args.server+"/api/"+parent+"/"+v)
                yield v
            if isinstance(v, dict):
                for result in find_keys(key, v, k):
                    yield result
            elif isinstance(v, list):
                for d in v:
                    for result in find_keys(key, d, k):
                        yield result


def recurse_objects(url):
    # prevent infinite recursion
    if url not in spidered and url.split("/")[5] not in excluded_objects:
        spidered.add(url)
        response=requests.get(url+".json"+"?fields=:all&paging=false",auth=AUTH)

        if response.status_code == requests.codes['OK']:
            collection = response.json()
            for m in find_keys("id", collection):
                package_ids.add(m)
            for ob in ["chart", "mapView", "reportTable", "eventReport", "eventChart", "indicator", "categoryOption", "category", "categories", "categoryOption", "categoryOptionCombo", "categoryCombo", "legendSet", "categoryOptionGroupSet"]:
                for obs in find_keys(ob, collection):
                    # print("OB1",ob,obs)
                    if "id" in obs:
                        recurse_objects(args.server+"/api/"+ob+"/"+obs["id"])
                for obs in find_keys(ob+"s", collection):
                    # print("OB2",ob,obs)
                    if "id" in obs:
                        recurse_objects(args.server+"/api/"+ob+"/"+obs["id"])
            for h in find_keys("href", collection):
                # print("------> href:",h)
                if h != url:
                    if url.split("/")[6] not in package_ids:
                        recurse_objects(h)

def get_exported_ids():

    try:
        export_response=requests.get(metadata_extract_config_root+"COVID19_AGG/COVID19_AGG_COMPLETE_V1_DHIS2.30/metadata.json")
        if export_response.status_code == requests.codes['OK']:
            export=json.loads(export_response.text)
            for m in find_ids("id", export):
                package_ids.add(m)
        else:
            print("Cannot retrieve export details. Exiting.")
            exit(1)
    except KeyError:
        print("Cannot retrieve export details. Exiting.")
        exit(1)


def get_package_ids():

    try:
        for g in export['_sharing']['groups']:
            collection = (requests.get(args.server+"/api/userGroups/"+g['id']+".json"+"?fields=:all&paging=false",auth=AUTH)).json()
            for m in find_keys("id", collection):
                package_ids.add(m)
    except KeyError:
                pass

    try:
        for c in export['customObjects']:
            type=c["objectType"]
            for i in c["objectIds"]:
                collection = (requests.get(args.server+"/api/"+type+"/"+i+".json"+"?fields=:all&paging=false",auth=AUTH)).json()
                for m in find_keys("id", collection):
                    package_ids.add(m)
    except KeyError:
                pass

# ["charts", "mapViews", "reportTables", "eventReports", "eventCharts"]

		# switch (types[k]) {
		# case "categoryOptions":
		# 	defaultDefault = "xYerKDKCefk";
		# 	break;
		# case "categories":
		# 	defaultDefault = "GLevLNI9wkl";
		# 	break;
		# case "categoryOptionCombos":
		# 	defaultDefault = "HllvX50cXC0";
		# 	break;
		# case "categoryCombos":
		# 	defaultDef

    for resource in ["dashboardIds", "dataElementGroupIds", "dataSetIds", "indicatorGroupIds", "programIds", "validationRuleGroupIds"]:
        try:
            print("resource", resource)
            if resource in export:
                for r in export[resource]:
                    print("r", r)
                    object_url=args.server+"/api/"+resource.replace('Ids','s')+"/"+r
                    recurse_objects(object_url)

                    # collection = (requests.get(+".json"+"?fields=:all&paging=false",auth=AUTH)).json()
                    # for m in find_keys("id", collection):
                    #     package_ids.add(m)
                    # for ob in ["chart", "mapView", "reportTable", "eventReport", "eventChart", "categoryOption", "categorie", "categoryOptionCombo", "categoryCombo"]:
                    #     for obs in find_keys(ob, collection):
                    #         print(ob,"in",r)
                    #         print(ob,obs)
                    # for h in find_keys("href", collection):
                    #     print("------> href:",h)
        except KeyError:
            print("error")
            pass
    print("got Ids")


if __name__ == "__main__":

    config_response=requests.get(metadata_extract_config_root+pack)

    if config_response.status_code == requests.codes['OK']:
        config=json.loads(config_response.text)

        for export in config['export']:

            fromDHIS2={}
            package_ids = set()
            # spidered= set()
            #
            resource_slug="package-"+export['_code']
            # print(resource_slug)
            #
            get_exported_ids()

            metadata_to_json()
            # json_to_transifex()

    else:
        print("Unable to retrieve config file from",metadata_extract_config_root+pack+metadata_extract_config_suffix)
        exit(1)
