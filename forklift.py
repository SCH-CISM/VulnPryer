#!/usr/bin/env python

import ConfigParser
from lxml import objectify
import gzip
import urllib2
import base64
import os
from lxml import etree
import pandas as pd
import logging
import tempfile
import re

logger = logging.getLogger('vulnpryer.forklift')

config = ConfigParser.ConfigParser()
config.read('vulnpryer.conf')

trl_source_url = config.get('RedSeal', 'trl_url')
username = config.get('RedSeal', 'username')
password = config.get('RedSeal', 'password')
temp_directory = config.get('VulnDB', 'working_dir')
s3_bucket = config.get('S3', 'bucket_name')
s3_region = config.get('S3', 'region')
s3_key = config.get('S3', 'key')


class HeadRequest(urllib2.Request):
    def get_method(self):
        return "HEAD"


def _read_trl(trl_location):
    """Read and Import TRL"""

    parsed = objectify.parse(gzip.open(trl_location))
    root = parsed.getroot()

    return root


def get_trl(trl_path):
    """Getch the TRL from RedSeal"""

    req = urllib2.Request(trl_source_url)
    base64str = base64.encodestring('%s:%s' % (username,
                                    password)).replace('\n', '')
    req.add_header("Authorization", "Basic %s" % base64str)
    result = urllib2.urlopen(req)

    with open(trl_path, "wb") as local_file:
        local_file.write(result.read())
        local_file.close()


def _read_vulndb_extract():
    """read in the extracted VulnDB data"""
    vulndb = pd.read_csv(temp_directory + 'vulndb_export.csv')
    return vulndb


def _remap_trl(trl_data, vulndb):
    """Rectify CVSS Values"""

    avg_cvss_score = 6.2
    msp_factor = 2.5
    edb_factor = 1.5
    private_exploit_factor = .5
    network_vector_factor = 2
    impact_factor = 3

    for vulnerability in trl_data.vulnerabilities.vulnerability:
        # start off with the NVD definition
        modified_score = float(vulnerability.get('CVSSTemporalScore'))
        # add deviation from mean
        modified_score = modified_score + (modified_score -
                                           avg_cvss_score) / avg_cvss_score
        # adjust up if metasploit module exists
        if vulndb[vulndb['CVE_ID'] ==
                  vulnerability.get('cveID')].msp.any >= 1:
                    modified_score = modified_score + msp_factor
        # adjust up if exploit DB entry exists
        if vulndb[vulndb['CVE_ID'] ==
                  vulnerability.get('cveID')].edb.any >= 1:
                    modified_score = modified_score + edb_factor
        # adjust up if a private exploit is known
        if vulndb[vulndb['CVE_ID'] ==
                  vulnerability.get('cveID')].private_exploit.any >= 1:
                    modified_score = modified_score + private_exploit_factor
        else:
            modified_score = modified_score - private_exploit_factor
        # adjust down for impacts that aren't relevant to our loss scenario
        if (vulndb[vulndb['CVE_ID'] ==
            vulnerability.get('cveID')].impact_integrity.any < 1 and
            vulndb[vulndb['CVE_ID'] ==
                   vulnerability.get('cveID')].impact_confidentiality.any < 1):
                modified_score = modified_score - impact_factor
        # adjust down for attack vectors that aren't in our loss scenario
        if vulndb[vulndb['CVE_ID'] ==
                  vulnerability.get('cveID')].network_vector.any < 1:
                    modified_score = modified_score - network_vector_factor
        # confirm that our modified score is within max/min limits
        if modified_score > 10:
            modified_score = 10
        if modified_score < 0:
            modified_score = 0
        # set the modified score
        vulnerability.set('CVSSTemporalScore', str(modified_score))
    return trl_data


def _write_trl(trl_data, modified_trl_path):
    """Write the modified trl out to disk"""
    # etree.cleanup_namespaces(trl)
    obj_xml = etree.tostring(trl_data, xml_declaration=True,
                             pretty_print=True, encoding='UTF-8')
    with gzip.open(modified_trl_path, "wb") as f:
        f.write(obj_xml)


def _fixup_trl(modified_trl_path):
    """Fix attribute order for trl node which RS 7.x is particular about"""
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    output_file = gzip.open(temp_file.name, "wb")
    reg_expression = '^<trl (.+) (publishedOn=\".+?\" version=\".+?\")>$'
    reg_expression = re.compile(reg_expression)
    fh = gzip.open(modified_trl_path, "rb")
    for line in fh:
        line = re.sub(reg_expression, r'<trl \2 \1>', line)
        output_file.write(line)
    fh.close()
    output_file.close()
    os.rename(temp_file.name, modified_trl_path)


def modify_trl(original_trl):
    """public full trl modification script"""
    vulndb = _read_vulndb_extract()
    trl_data = _read_trl(original_trl)
    modified_trl_data = _remap_trl(trl_data, vulndb)

    new_trl_path = os.path.dirname(original_trl) + '/modified_trl.gz'
    _write_trl(modified_trl_data, new_trl_path)
    _fixup_trl(new_trl_path)
    return new_trl_path


def post_trl(file_path):
    """store the TRL to S3"""

    from filechunkio import FileChunkIO
    import math
    import os
    import boto.s3
    conn = boto.s3.connect_to_region(s3_region)

    bucket = conn.get_bucket(s3_bucket, validate=False)

    logger.info('Uploading {} to Amazon S3 bucket {}'.format(
        file_path, s3_bucket))

    import sys

    def percent_cb(complete, total):
        sys.stdout.write('.')
        sys.stdout.flush()

    source_size = os.stat(file_path).st_size
    chunk_size = 10000000
    chunk_count = int(math.ceil(source_size / chunk_size))
    mp = bucket.initiate_multipart_upload(s3_key, encrypt_key=True,
                                          policy='public-read')
    for i in range(chunk_count + 1):
        offset = chunk_size * i
        bytes = min(chunk_size, source_size - offset)
        with FileChunkIO(file_path, 'r', offset=offset, bytes=bytes) as fp:
            mp.upload_part_from_file(fp, part_num=i + 1)
    mp.complete_upload()

    # old single part upload not used due to bug in boto with continuation
    # headers
    # from boto.s3.key import Key
    # k = Key(bucket)
    # k.key = key_name
    # k.set_contents_from_filename(file_path, cb=percent_cb, num_cb=10,
    #   encrypt_key=True, policy='public-read')

    return

if __name__ == "__main__":
    modify_trl('/tmp/trl.gz')
