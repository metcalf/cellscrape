import urllib2
import simplejson
import optparse
import sys
import csv
import urllib
import time
import re
from collections import defaultdict, OrderedDict

from bs4 import BeautifulSoup


GAPI_KEY = "AIzaSyB8fwNPwYjTeEbZU0TT1ZvaMes2_dqvGyo"
CUSTOM_SEARCH = "https://www.googleapis.com/customsearch/v1?key=%s&cx=015988297936601976182:uvoaw7yqzou"%GAPI_KEY

PIXEL_RE = re.compile(r"(\d+)\s?x\s?(\d+)", re.IGNORECASE)
SIZE_RE = re.compile(r"(\d+(\.\d+)?)\s?inches", re.IGNORECASE) 
MIDP_RE = re.compile(r"MIDP (\d+(\.\d+)?)", re.IGNORECASE)
VER_RE = re.compile(r"(\d+(\.\d+)?)", re.IGNORECASE)
HTML_RE = re.compile(r"(^|[^x])HTML", re.IGNORECASE)

def search(name):
    result = ""
    url = "".join((CUSTOM_SEARCH, "&q=",urllib.quote_plus(name), 
                   "&exactTerms=", "Full+Phone+Specifications"))
    request = urllib2.Request(
        url, None, {'Referer': "http://kenya.throughawall.com"})
    response = urllib2.urlopen(request)
    data = simplejson.load(response)
    items = data.get("items")
    if items:
        if "- Full phone specifications" in items[0]["title"]:
            result = items[0]["link"]
        else:
            print "Title doesn't appear to be valid: %s"%items[0]["title"]
    else:
        print "No items returned for %s"%name

    print "%s: %s"%(name, result)
    return result

def scrape(uri):
    results = []
    request = urllib2.Request(uri)
    response = urllib2.urlopen(request)
    
    # Extract div#specs-list
    # For each table
    # Read table name from th in first tr
    # For each tr
    # Read key-value pairs from td.ttl and td.nfo

    soup = BeautifulSoup(response, "html5lib")

    specs = soup.find(id="specs-list")
    if not specs:
        print "No specs for %s"%uri
        return None

    for table in specs.find_all("table"):
        try:
            category = unicode(table.find("th").string)
        except Exception as e:
            print "Error parsing table for %s: %s"(uri, e)
            continue
        for row in table.find_all("tr"):
            if not row.find("td", class_="ttl"):
                continue # Skip blanks
            try:
                results.append({
                        "category": category.strip(),
                        "subcategory": unicode(row.find("td", class_="ttl").string).strip(),
                        "value": unicode(row.find("td", class_="nfo").string).strip()
                        })
            except Exception as e:
                print "Error parsing row for %s: %s\n%s"%(uri, row, e)

    print "Scraped %s"%uri
    return results
    
def parse(datum):
    result = OrderedDict(datum["metadata"])

    if not datum.get("raw"):
        return result


    tree = defaultdict(dict)
    for row in datum["raw"]:
        tree[row["category"].lower().strip()][row["subcategory"].lower()] = row["value"]

    general = tree["general"]
    data = tree["data"]
    features = tree["features"]

    if "No" not in general.get("4g network", "No"):
        result["Network"] = "4G"
    if "No" not in general.get("3g network", "No"):
        result["Network"] = "3G"
    elif "No" not in general.get("2g network", "No"):
        result["Network"] = "2G"
    else:
        result["Network"] = "Other"

    for tech in ("lte", "dc-hsdpa", "hsdpa", "ev-do", "hsupa"):
        if tech in data.get("speed", "").lower():
            result["Data"] = tech.upper()
            break
    else:
        if result["Network"] == "4G":
            result["Data"] = "Other 4G"
        elif result["Network"] == "3G":
            result["Data"] = "Other 3G"
        elif "No" not in data.get("edge", "No"):
            result["Data"] = "EDGE"
        elif "No" not in data.get("gprs", "No"):
            result["Data"] = "GPRS"
        else:
            result["Data"] = "None"

    result["GPS"] = "Yes" if ("Yes" in features.get("gps", "")) else "No"
    result["Video"] = "Yes" if ("Yes" in tree["camera"].get("video", "")) else "No"
    
    if "No" in tree["camera"].get("primary", "No"):
        result["Camera"] = "No"
    else:
        c_match = PIXEL_RE.search(tree["camera"].get("primary", ""))
        result["Camera"] = c_match.group(0).replace(" ", "") if c_match else "Yes"
    
    dr_match = PIXEL_RE.search(tree["display"]["size"])
    result["Display Resolution"] = dr_match.group(0).replace(" ", "") if dr_match else "Unknown"

    ds_match = SIZE_RE.search(tree["display"]["size"])
    result["Display Size (inches)"] = ds_match.group(1) if ds_match else "Unknown"

    if "No" in features.get("java", "No"):
        result["Java"] = "No"
    else:
        midp_match = MIDP_RE.search(features["java"])
        result["Java"] = midp_match.group(0) if midp_match else "Yes"

    msging = features["messaging"].lower().replace("instant messaging", "im")
    for msg in ("sms", "mms", "mail", "im"): 
        result[msg.upper()] = "Yes" if msg in msging else "No"
        
    result["OS"] = ""
    result["OS Version"] = ""
    for os in ("Android", "iOS", "Symbian", "Blackberry", "Windows"):
        if os.lower() in features.get("os", "").lower():
            result["OS"] = os
            osv_match = VER_RE.search(features["os"])
            if osv_match:
                result["OS Version"] = osv_match.group(0)
            break
    
    if "No" not in features.get("browser", "No"):
        if HTML_RE.search(features["browser"]):
            result["Browser"] = "HTML"
        elif "wap" in features["browser"].lower():
            result["Browser"] = "WAP"
        else:
            result["Browser"] = "Other"
    else:
        result["Browser"] = "No"
        

    keys = (
        ("features", "os"),
        ("features", "browser"),
        )
    
    for cat, sub in keys:
        result["RAW %s - %s"%(cat, sub)] = tree[cat].get(sub, "")
        
    return result

def main():
    parser = optparse.OptionParser(usage='%prog [mode] [options]')
    parser.add_option("-i", "--input", action='store', dest="infilename",
                      help="Input file path")
    parser.add_option("-o", "--output", action='store', dest="outfilename", type="string",
                      help="Output file path")
    parser.add_option("-s", "--offset", action='store', dest="offset", type="int",
                      help="Start offset")
    parser.add_option("-c", "--count", action='store', dest="count", type="int",
                      help="Records to process")
    parser.set_defaults(count=0, offset=0)
    options, args = parser.parse_args()
    
    infile = open(options.infilename, "r")
    outfile = open(options.outfilename, "w")

    if args[0] == "search":
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        header = reader.next()
        if not "uri" in header:
            header.append("uri")
        uri_col = header.index("uri")
        name_col = header.index("name")
        writer.writerow(header)
        for i, row in enumerate(reader):
            if i >= options.offset and (options.count < 1 or i < (options.offset+options.count)):
                res = search(row[name_col])
                time.sleep(1.1)
                if len(row) < len(header):
                    row.append(None)
                row[uri_col] = res
            writer.writerow(row)
    elif args[0] == "scrape":
        reader = csv.reader(infile)
        results = []
        header = reader.next()
        uri_col = header.index("uri")
        name_col = header.index("name")
        for i, row in enumerate(reader):
            result = {
                "metadata": dict(zip(header, row)),
                "raw": None
                }
            if (len(row) > uri_col and row[uri_col] and 
                i >= options.offset and 
                (options.count < 1 or i < (options.offset+options.count))):
                result["raw"] = scrape(row[uri_col])
            results.append(result)

        simplejson.dump(results, outfile)
    elif args[0] == "parse":
        indata = simplejson.load(infile)
        writer = csv.writer(outfile)
        header = ["name", "Subscribers", "uri"]
        rows = []

        for datum in indata:
            parsed = parse(datum)
            for k in parsed:
                if k not in header:
                    header.append(k)
            row = [""]*len(header)
            for k, v in parsed.iteritems():
                row[header.index(k)] = v
            rows.append(row)

        writer.writerow(header)
        writer.writerows(rows)
        

    

if __name__ == '__main__':
    main()

