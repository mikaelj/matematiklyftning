import uno
from com.sun.star.beans import PropertyValue
def oo_calc(uri='private:factory/scalc'): #if no uri is passed, open a blank calc document
    localContext = uno.getComponentContext()
    resolver = localContext.ServiceManager.createInstanceWithContext('com.sun.star.bridge.UnoUrlResolver',localContext)
    ctx = resolver.resolve('uno:socket,host=localhost,port=5038;urp;StarOffice.ComponentContext')
    p = PropertyValue()
    p.Name = 'Hidden'
    p.Value = True
    properties = (p,)
    desktop = ctx.ServiceManager.createInstance('com.sun.star.frame.Desktop')
    return desktop.loadComponentFromURL(uri,'_blank',0,properties)

def get_sheet(index, workbook):
    """Return the desired sheet. If the index is wrong, return the 0th sheet"""
    sheets = workbook.getSheets()
    if index >= sheets.getCount():
        print "Warning: Index out of range. Returning Ist Sheet"
        index = 0
    return sheets.getByIndex(index)

def set_cell(sheet, row, col, data):
    xCell = sheet.getCellByPosition(col,row)
    if type(data) in (type(str()), type(unicode())): #String/Unicode type?
        xCell.setString(data)
    else:
        #assume a numeric value
        try:
            xCell.setValue(data)
        except: #Ignore cells with invalid data
            print 'Invalid data',data

def save_document_as(calc,filename,overwrite):
    p = PropertyValue()
    p.Name = 'Overwrite'
    p.Value = overwrite
    properties = (p,)
    calc.storeAsURL('file://'+filename,properties)

def save_document(calc):
    calc.store()

def optimise_column_widths(sheet,n):
    """optimise_column_widths(sheet,4)"""
    columns = sheet.getColumns()
    for col in range(n):
        column = columns.getByIndex(col)
        column.setPropertyValue('OptimalWidth', True)

def get_cell(sheet,row,col):
        EMPTY= uno.Enum("com.sun.star.table.CellContenType", "EMPTY")
        TEXT = uno.Enum("com.sun.star.table.CellContentType","TEXT")
        FORMULA = uno.Enum("com.sun.star.table.CellContentType","FORMULA")
        VALUE = uno.Enum("com.sun.star.table.CellContentType","VALUE")
        xcell = sheet.getCellByPosition(col,row)
        datatype = xcell.getType()
        if datatype == EMPTY:
            return None
        elif datatype == VALUE:
            return xcell.getValue()
        else:
            return xcell.getString()

