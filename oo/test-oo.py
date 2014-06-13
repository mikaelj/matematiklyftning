#!/usr/bin/env python

from openoffice import *

#
# App
#
def main():
    print """soffice --invisible '--accept=socket,host=localhost,port=5038;urp;'"""
    calc = oo_calc("file:///tmp/tmp.ods")
    sheet = get_sheet(0, calc)
    sheet.setName("Hello")
    save_document(calc)

if __name__ == '__main__':
    main()


