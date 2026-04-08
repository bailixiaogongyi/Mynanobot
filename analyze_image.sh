#!/bin/sh
du -sh /usr/local/lib/python3.12/site-packages/* 2&gt;/dev/null | sort -hr | head -30
