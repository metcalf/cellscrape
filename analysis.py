import csv
import optparse
import itertools
from collections import defaultdict
from prettytable import PrettyTable

PCT_FORMAT = lambda x: "%0.1f%%"%(x*100)

def resolution_sort(v):
    v = v[0]
    try:
        w, h = v.split("x")
    except ValueError:
        if v == "Yes":
            return 0
        elif v == "No":
            return 1
        elif v == "Unknown":
            return 2
        elif v == "(blank)":
            return 3
        else:
            raise ValueError("Invalid resolution %s"%v)
    else:
        return -int(w)*int(h)

def float_sort(v):
    v = v[0]
    try:
        return -float(v)
    except ValueError:
        return v

def get_list_sort(ls):
    def list_sort(v):
        v = v[0]
        try:
            return ls.index(v)
        except ValueError:
            print "%s not in list %s"%(v, ls)
            raise
    return list_sort

def default_sort(v):
    v = v[0]
    if v == "(blank)":
        return "zzzz"
    if v == "Yes":
        return 0
    elif v == "No":
        return 1
    else:
        return v

SORTING = {
    "Browser": ("HTML", "WAP", "No", "(blank)"),
    "Java": ("MIDP 2.1", "MIDP 2.0", "MIDP 1.0", "Yes", "No", "(blank)"),
    "Display Size (inches)": float_sort,
    "Display Resolution": resolution_sort,
    "Camera": resolution_sort,
    "Data": ("HSDPA", "Other 3G", "EDGE", "GPRS", "Other 2G", "None", "(blank)"),
    "Network": ("3G", "2G", "(blank)"),
}

def get_sort(col):
    sorting = SORTING.get(col)
    if sorting:
        if hasattr(sorting, "__iter__"):
            return get_list_sort(sorting)
        else:
            return sorting
    else:
        return default_sort

def main():
    parser = optparse.OptionParser(usage='%prog [mode] [options]')
    parser.add_option("-i", "--input", action='store', dest="infilename",
                      help="Input file path")
    parser.add_option("-e", "--exclude-blank", action='store', dest="infilename",
                      help="Exclude blanks from analysis")

    options, args = parser.parse_args()

    reader = csv.reader(open(options.infilename, "r"))

    header = reader.next()
    data = [r for r in reader]

    name_col = header.index("name")
    count_col = header.index("Subscribers")
    data_cols = range(3, 18)

    for data_col in data_cols:
        agg = defaultdict(int)
        total = 0.0
        cum = 0.0
        for row in data:
            label = row[data_col].strip()
            if not label:
                label = "(blank)"
            agg[label] += int(row[count_col])
            # Yea, totals should be the same
            total += int(row[count_col])

        lines = [[label, count, PCT_FORMAT(count / total), 0] 
                 for label, count in agg.iteritems()]
        lines.sort(key=get_sort(header[data_col]))
        
        table = PrettyTable((header[data_col], "Subscribers", "% of total", "% cumulative"))
        for line in lines:
            cum += line[1]
            line[3] = PCT_FORMAT(cum / total)
            table.add_row(line)
        
        print header[data_col]
        print table.get_string(sortby=header[data_col], sort_key=get_sort(header[data_col]))
        print 
        
if __name__ == '__main__':
    main()
