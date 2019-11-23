#!/bin/sh
#
# Retrieves all pages from the OAI interface.
# Usage: download.sh https://maior.memorix.nl/api/oai/raa/key/Elsinga/ ese
# (both parameters are optional, the above values are default)
#
# Dependencies: sh, curl, head, tail, awk, xmllint (Debian packages: curl coreutils gawk libxml2-utils)
#
# Author: Ivan Masar, 2014. Released into public domain.
# Author: Siebrand Mazeland, 2019. Released into public domain. Debugged and updated for https://phabricator.wikimedia.org/T235995
#set -x

oaibase="https://maior.memorix.nl/api/oai/raa/key/Elsinga/"
format="ese"
FILE_NUMBER=1
DIR_OUT="./download_data"
printf -v FILE_NAME '%05d' $FILE_NUMBER
tmpfile="$DIR_OUT/$FILE_NAME.xml"

export LC_ALL=C

if [ "$#" -ge 1 ]; then
        oaibase="$1"
fi

if [ "$#" -eq 2 ]; then
        format="$2"
fi

echo "OAI base URL = $oaibase"
echo "metadata format = $format"

curl -s "$oaibase?verb=ListRecords&metadataPrefix=$format" > $tmpfile
size=`xmllint --xpath "string(//*[local-name()='OAI-PMH']/*[local-name()='ListRecords']/*[local-name()='resumptionToken']/@completeListSize)" $tmpfile`
echo "completeListSize = $size"
perpage=`xmllint --xpath "count(//*[local-name()='OAI-PMH']/*[local-name()='ListRecords']/*[local-name()='record'])" $tmpfile`
echo "records per page = $perpage"

token=`xmllint --xpath "//*[local-name()='OAI-PMH']/*[local-name()='ListRecords']/*[local-name()='resumptionToken']/text()" $tmpfile`
page=0
until [ "$token" = "" ]; do
        page=$(($page+1))
        FILE_NUMBER=$(($FILE_NUMBER+1))
        printf -v FILE_NAME '%05d' $FILE_NUMBER
        tmpfile="$DIR_OUT/$FILE_NAME.xml"
        record=$(($page*$perpage))
        echo "record $record, $token"
        curl -s "$oaibase?verb=ListRecords&resumptionToken=$token" > $tmpfile
        token=`xmllint --xpath "//*[local-name()='OAI-PMH']/*[local-name()='ListRecords']/*[local-name()='resumptionToken']/text()" $tmpfile`
done
