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

logger = logging.getLogger('vulnpryer.apply')

config = ConfigParser.ConfigParser()
config.read('vulnpryer.conf')

def _loadplugins():
    """load plugins"""
    pass

def _load_source():
    """load the source"""
    pass

def _prioritize():
    """loop over the data and apply the new scores"""
    pass

def _write_output():
    """send modified data stream to output"""
    pass

def _send_notification():
    """when a vuln is modified, send a notification to channel of choice"""
    pass

if __name__ == "__main__":
    modify_trl('/tmp/trl.gz')
