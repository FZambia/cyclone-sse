#!/bin/bash
rpmbuild -bb cyclone_sse.spec --define "version 0.7.5" --define "release `date +%s`"