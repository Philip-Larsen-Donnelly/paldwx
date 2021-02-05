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
import tempfile

parser = argparse.ArgumentParser(description='Pull translations from dhis2 API and create files for transifex.')
parser.add_argument('-u','--user', action="store", help='dhis2 user', required=True)
parser.add_argument('-p','--password', action="store", help='dhis2 password', required=True)
parser.add_argument('-s','--server', action="store", help='dhis2 server instance', required=True)  # e.g. https://whom.dhis2.org/phil_dev
parser.add_argument('-r','--package_root', action="store", help='dhis2 metadata package root', required=True) # e.g. "https://raw.githubusercontent.com/dhis2/metadata-package-development/work-in-progress/metadata/"
parser.add_argument('-k','--package', action="store", help='dhis2 metadata package name', required=True) # e.g. "COVID19_AGG/COVID19_AGG_COMPLETE_V1_DHIS2.30/metadata.json"
parser.add_argument('-j','--project', action="store", help='dhis2 project name', required=True) # e.g. meta-who-packages
parser.add_argument('-t','--tx_token', action="store", help='transifex api token', required=True)
args = parser.parse_args()

localisation_dir = tempfile.TemporaryDirectory(prefix="i18n")
# localisation_dir = "i18n"
locale_file_pattern = localisation_dir.name + "/{p}_{l}.json"
source_file_pattern = localisation_dir.name + "/{p}.json"

locale_file_glob_pattern = localisation_dir.name + "/{p}_*.json"
locale_file_prefix = localisation_dir.name + "/{p}_"

#
# localisation_dir = "i18n"
# locale_file_pattern = localisation_dir + "/{p}_{l}.json"
# source_file_pattern = localisation_dir + "/{p}.json"
#
# locale_file_glob_pattern = localisation_dir + "/{p}_*.json"
# locale_file_prefix = localisation_dir + "/{p}_"


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
metadata_extract_config_root=args.package_root
metadata_extract_config_suffix="_export_conf.json"
excluded_objects=["organisationUnits","users","organisationUnit","user"]


# We need to map language codes that DHIS2 doesn't support natively
# uz@Cyrl --> uz
# uz@Latn --> uz_UZ
langmap={'uz@Cyrl':'uz','uz@Latn':'uz_UZ'}

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
            tfs = ''
            for transField in translatable_fields[resource]:
                tfs += ','+transField
            collection = (requests.get(args.server+"/api/"+resource+".json"+"?fields=id,translations"+tfs+"&paging=false",auth=AUTH)).json()[resource]
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

                                if m['locale'] not in langmap.keys():
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

    mfile= open("fromMeta.json",'w')
    mfile.write(json.dumps(fromDHIS2, sort_keys=True, indent=2, separators=(',', ': ')))
    mfile.close()

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
            delta[k] = out_trans[k]

    return delta

    # return delta

def json_to_metadata():

    print("Pushing translations to",args.server,"...")

    locales = {}

    for localefile in glob.iglob(locale_file_glob_pattern.format(p=args.package)):
        # print(localefile)

        lfile=open(localefile,'r')
        locale = json.load(lfile)
        lfile.close()

        locale_name = localefile.replace(locale_file_prefix.format(p=args.package),'').split('.')[0]
        if locale_name != 'en':
            # print("locale", locale)
            for resource in locale:
                # print("\tresource", resource)
                for id in locale[resource]:
                    for property in locale[resource][id]:
                        property_value = locale[resource][id][property]
                        if property_value:
                            translation = [{ "property": property, "locale": locale_name, "value": property_value }]
                            entry = { resource : { id : { "translations" : translation }}}
                            merge_translations(locales,entry)

        # locales.merge(locale)

    # print(json.dumps(locales, sort_keys=True, indent=2, separators=(',', ': ')))

    mfile= open("toMeta.json",'w')
    mfile.write(json.dumps(locales, sort_keys=True, indent=2, separators=(',', ': ')))
    mfile.close()

    # compare downloaded translations with those pulled from DHIS2, so that we only have
    # to push back updates
    toDHIS2 = minimise_translations(fromDHIS2,locales)

    mfile= open("toMetaMin.json",'w')
    mfile.write(json.dumps(toDHIS2, sort_keys=True, indent=2, separators=(',', ': ')))
    mfile.close()

    for resource in toDHIS2:
        for id in toDHIS2[resource]:
            payload = json.dumps(toDHIS2[resource][id], sort_keys=True, indent=2, separators=(',', ': '))
            url = args.server+"/api/"+resource+"/"+id+"/translations"
            # print("PUT ",url)
            r = requests.put(url, data=payload,auth=AUTH)
            print(r.status_code,": PUT ",url)
            # print(payload)
            if r.status_code > 204:
                print(payload)
                print(r.headers)



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


def transifex_to_json():

    print("Pulling translations from transifex...")

    langs = []
    urll = tx_langs_api.format(s=project_slug, r=resource_slug)
    response = requests.get(urll, auth=TX_AUTH)
    if response.status_code == requests.codes['OK']:
        langs= (x['code'] for x in response.json()['available_languages'])
        # print(langs)

    for language_code in langs:
        # print(language_code)

        # We need to map language codes that DHIS2 doesn't support natively
        # uz@Cyrl --> uz
        # uz@Latn --> uz_UZ
        # mapped_language_code = language_code.replace("@Latn","_UZ").replace("@Cyrl","")
        mapped_language_code = language_code
        if language_code in langmap.keys():
            mapped_language_code = langmap[language_code]

        urls = tx_stats_api.format(s=project_slug, r=resource_slug, l=language_code)
        response = requests.get(urls, auth=TX_AUTH)
        if response.status_code == requests.codes['OK']:
            trans=response.json()['translated_entities']

            if trans > 0:
                # If there are any translations for this language code in transifex, download them
                print(language_code,":", trans, "translations. Downloading")

                path_to_file=locale_file_pattern.format(p=args.package, l=mapped_language_code)
                url = tx_translations_api.format(s=project_slug, r=resource_slug, l=language_code, m=tx_mode)
                response = requests.get(url, auth=TX_AUTH)
                if response.status_code == requests.codes['OK']:

                    os.makedirs(os.path.dirname(path_to_file), exist_ok=True)
                    with open(path_to_file, 'wb') as f:
                        for line in response.iter_content():
                            f.write(line)
            else:
                # If there are no translations currently in transifex, check if we have some existing
                # translations from DHIS2 and push them to transifex
                for localefile in glob.iglob(locale_file_glob_pattern.format(p=args.package)):

                    lfile=open(localefile,'r')
                    locale = json.load(lfile)
                    lfile.close()

                    locale_name = localefile.replace(locale_file_prefix.format(p=args.package),'').split('.')[0]
                    if locale_name == mapped_language_code:
                        print(language_code,"has no translations in transifex. Pushing existing translations to transifex.")

                        url = tx_translations_update_api.format(s=project_slug, r=resource_slug, l=language_code)
                        content = open(localefile, 'r').read()
                        data = {'content': content}
                        r = requests.put(
                             url, data=json.dumps(data), auth=TX_AUTH, headers={'content-type': 'application/json'},
                        )
                        print(r.status_code,": PUT ",url)



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


if __name__ == "__main__":

    export_response=requests.get(metadata_extract_config_root+pack)

    if export_response.status_code == requests.codes['OK']:
        export=json.loads(export_response.text)

        fromDHIS2={}
        package_ids = set()
        # spidered= set()
        #
        resource_slug="package-"+pack.split("/")[0]
        # print(resource_slug)
        #
        for m in find_ids("id", export):
            package_ids.add(m)

        metadata_to_json()
        json_to_transifex()
        transifex_to_json()
        json_to_metadata()

    else:
        print("Unable to retrieve config file from",metadata_extract_config_root+pack+metadata_extract_config_suffix)
        exit(1)
