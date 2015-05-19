
# -*- coding: utf-8 -*-


import sys
import os

import struct

import pdb
kwdbg = True
kwlog = True

import pprint
pp = pprint.pprint

import c64Data
fontmapping = c64Data.fontmapping
c64colors = c64Data.c64colors
GEOSDirEntry = c64Data.GEOSDirEntry
GEOSHeaderBlock = c64Data.GEOSHeaderBlock


SUPPRESS_NUL = False
FF_TO_LF = False

import PIL
import PIL.Image
import PIL.ImageDraw


def expandImageStream( s ):
    n = len(s)
    j = -1
    image = []
    while j < n-1:
        j += 1
        code = ord(s[j])
        
        if code < 128:
            data = ord(s[j+1])
            t = [data] * code
            image.extend( t )
            j += 1
            continue
        elif 128 <= code <= 219:
            c = code - 128
            data = s[j+1:j+c+1]
            for i in data:
                image.append( ord(i) )
            j += c
            continue
            
        else:
            # 220...255
            patsize = code -220
            repeat = ord(s[j+1])
            size = repeat * patsize
            pattern = s[j+2:j+2+patsize]
            for i in range( repeat ):
                for p in pattern:
                    image.append( ord(p) )
            
            j += patsize + 1
            continue
    return image



def photoScrap( s ):
    if s == None:
        return
    cardsw = ord(s[0])
    w = cardsw * 8
    h = ord(s[2]) * 256 + ord(s[1])
    cardsh = h >> 3
    noofcards = cardsw * cardsh
    image = []
    
    image = expandImageStream(s[3:])

    colorbands = []
    # extract color data
    offset = cardsw * h
    for row in range(cardsh):
        base = offset + row * cardsw
        end = base + cardsw
        band = image[base:end]
        colorbands.append( band )

    # pdb.set_trace()

    # new image
    img = PIL.Image.new('1', (w,h), 0)
    
    draw = PIL.ImageDraw.Draw( img )
    # fill background colors
    if 0:
        for row in range(cardsh):
            base = row * cardsw
            for col in range(cardsw):
                idx = base + col
                x = col * 8
                y = row * 8
                color = colorbands[row][col]
                bg = color & 15
                bg = c64colors[bg]
                fg = (color >> 4) & 15
                fg = c64colors[fg]
                # draw.rectangle( (x,y,x+8,y+8), fill=bg)

                bytes = []
                for i in range(8):
                    byteadr = base 
                    bitmapbyte = image[idx + i * cardsw]
                    bytes.append( chr(bitmapbyte) )
                bytes = ''.join(bytes)
                card = PIL.Image.frombytes('1', (8,8), bytes, decoder_name='raw')
                img.paste(card, (x,y,x+8,y+8))

    bytes = []
    for y in range(h):
        for x in range(cardsw):
            idx = y * cardsw + x
            print idx,
            cardbyte = image[idx]
            cardbyte = cardbyte ^ 0xff
            bytes.append( chr(cardbyte) )
        print

    bytes = ''.join( bytes )
    img = PIL.Image.frombytes('1', (w,h), bytes, decoder_name='raw')
    img.save("test.png")
    pdb.set_trace()
    return (w,h,image)


def main():
    argc = len(sys.argv)
    
    if argc < 3:
        print "Usage: %s <infile> <outfile.rtf|outfile.html|outfile.txt>" % sys.argv[0]
        print "\nThis tool converts a C64/C128 GEOS GeoWrite .CVT file into an RTF, HTML,"
        print "or plain-text file, depending on the file extension of <outfile>."
        print "All graphics information will be discarded. Choose RTF for best results.\n"
        exit(1)

    # pdb.set_trace()

    infile = sys.argv[1]
    infile = os.path.abspath(os.path.expanduser(infile))

    outfile = sys.argv[2]
    outfile = os.path.expanduser(os.path.abspath(outfile))
    
    folder, filename = os.path.split( outfile )
    basename, ext = os.path.splitext( filename )

    print_html = False
    print_rtf = False
    
    if ext.lower() in (".rtf", ".rtfd"):
        print_rtf = True
    
    if ext.lower() in (".htm", ".html"):
        print_html = True

    f = open(infile, 'rb')
    data = f.read()
    f.close()

    f = open(outfile, 'w')

    direntry = data[0:0x1e]

    gde = GEOSDirEntry(direntry)
    gde.prnt()
    
    fname = data[3:19]
    format = data[0x1e:0x3a]

    geoinfo = data[0xfe:0x1fc]
    pdb.set_trace()    
    gib = GEOSHeaderBlock(geoinfo)
    gib.prnt()
    
    giwidth = ord( geoinfo[0] ) * 8
    giheight = ord( geoinfo[1] )
    gibitmapType = ord( geoinfo[2] )
    gispritedata = geoinfo[3:66]
    
    gidosfiletype = ord( geoinfo[66] )
    gigeosfiletype = ord( geoinfo[67] )
    gigeosfilestructure = ord( geoinfo[68] )
    
    if kwlog:
        print "icon width:", giwidth
        print "icon height:", giheight
        print "bitmap type", gibitmapType
        print "DOS file type:", gidosfiletype
        print "GEOS file type:", gigeosfiletype
        print "GEOS file structure:", gigeosfilestructure
    

    geofiletype = ord(data[21])
    
    vlirheader = data[0x1fc:0x2fa]

    if format.startswith("PRG formatted GEOS file V1.0"):
        broken = False
    elif format.startswith("PRG formatted GEOS file"):
        broken = True
    else:
        print "ERROR: Unknown file format %s" % repr(format)

    if kwlog:
        print "<<<%s>>>" % format

    payload = data[0x2FA:]

    if print_rtf:
        f.write("{\\rtf1 ")

    chains = [ None ] * 127
    
    consumedpayload = 0
    
    # pdb.set_trace()

    for i in range( 127 ):
        a1 = ord( vlirheader[i * 2] )
        a2 = ord( vlirheader[i * 2 + 1] )
        if kwlog:
            print "<<<chain 0x%02x/0x%02x>>>" % ( a1, a2 )
        
        # end of file
        if a1 == 0 and a2 == 0:
            #chains[i] = (ai,a2)
            break
        
        if a1 == 0 and a2 == 255:
            #chains[i] = (ai,a2)
            continue
        
        if broken:
            chain_size = a1 * 254 + a2
            gross_size = chain_size
        else:
            chain_size = (a1 - 1) * 254 + a2 -1
            gross_size = a1 * 254

        chainstart = consumedpayload
        chainend = consumedpayload + gross_size
        chainlogicalend = consumedpayload + chain_size
        chaindata = payload[chainstart:chainlogicalend]
        
        chains[i] = chaindata

        consumedpayload = chainend

    # pdb.set_trace()
    
    log = []
    # geowrite

    for idx,chain in enumerate(chains):

        if not chain:
            continue

        if idx >= 61:
            break

        style = 0
        font_size = 0
        font_id = 0
        n = len(chain)
        j = -1
        while j < n-1:
            j += 1
            dist = n - j
            if dist <= 2:
                # pdb.set_trace()
                pass
            c = chain[j]
            nc = ord(c)

            if nc == 0:
                if j == 0:
                    if kwlog:
                        print "<<<Unknown Escape 0x00>>>"
                    j += 19
                    log.append("0x00 at start")
                    continue
                if SUPPRESS_NUL:
                    continue

            elif nc == 12:
                if FF_TO_LF:
                    f.write("\n")
                    
                    continue
                else:
                    if print_html:
                        f.write("<hr/>\n")
                    else:
                        f.write("\\page ")
                    log.append("LF")
                    continue

            elif nc == 13:
                if print_html:
                    f.write("<br/>\n")
                elif print_rtf:
                    f.write("\\\n")
                else:
                    f.write("\n")
                log.append("RET")
                continue;

            elif nc == 16:
                # graphics escape
                
                width = ord(chain[j+1]) * 8
                heightL = ord(chain[j+2])
                heightH = ord(chain[j+3])
                height = heightH * 256 + heightL
                chainindex = ord(chain[j+4])
                if kwlog:
                    print "+++ TODO +++   <<<Graphics Escape>>> %i:%i @ VLIR:%i" % (width, height, chainindex)
                if print_rtf and False:
                    f.write("{{\\NeXTGraphic attachment \\width%d \\height%d} ¬}" % (width * 20, height * 20))

                # pdb.set_trace()
                if  63 <= chainindex <= 127:
                    i = photoScrap( chains[chainindex] )
                else:
                    pdb.set_trace()
                    print "INDEX ERROR"
                j += 4
                log.append("GRPHX %i" % chainindex)
                continue

            elif nc == 17:
                # ruler escape
                leftMargin = struct.unpack("<H", chain[j+1:j+3])[0]
                rightMargin = struct.unpack("<H", chain[j+3:j+5])[0]

                s1 = j+5
                s2 = j+7
                dec = 2**15
                tabs = []
                for i in range(8):
                    tab = struct.unpack("<H", chain[s1:s2])[0]
                    if tab & dec:
                        tab -= dec
                        tabs.append( (tab, 1) )
                    else:
                        tabs.append( (tab, 0) )
                    s1 += 2
                    s2 += 2

                paragraphMargin = struct.unpack("<H", chain[j+21:j+23])[0]

                justifiation = ord( chain[j+23] ) & 3

                spacing = ord( chain[j+23] ) >> 2 & 3
                
                color = ord( chain[j+24] )
                
                justifications = {
                    0:  'left',
                    1:  'center',
                    2:  'right',
                    3:  'justify'}
                
                if print_rtf:
                    if spacing == 0:
                        f.write("\\sl240 ")
                    elif spacing == 1:
                        f.write("\\sl360 ")
                    elif spacing == 2:
                        f.write("\\sl480 ")
                
                    f.write("\\q%s " % (justifications[justifiation],))

                if print_html:
                    #no line spacing ?!?
                    f.write('<span align="%s">' % (justifications[justifiation],))
                
                if kwlog:
                    print "leftmargin:", repr(leftMargin)
                    print "rightMargin:", repr(rightMargin)
                    print "paragraphMargin:", repr(paragraphMargin)
                    print "justifiation:", repr(justifiation)
                    print "spacing:", repr(spacing)
                    print "color:", repr(color)
                    print "tabs:"
                    pp(tabs)
                j += 26
                log.append("RULER")
                continue

            elif nc == 23:
                # NEWCARDSET
                fontL = ord(chain[j+1])
                fontH = ord(chain[j+2])
                newfont = fontH * 256 + fontL
                fontid = newfont >> 5
                fontsize = newfont & 0x1f
                newstyle = ord(chain[j+3])
                
                if kwlog:
                    print "segment:", repr(chain[j:j+4])
                    print "<<<NEWCARDSET Escape>>>"
                    print "fontID:", fontid
                    print "font size:", fontsize
                    print "style:", bin(style)
                
                if fontid != font_id:
                    font_id = fontid

                if fontsize != font_size:
                    if print_html:
                        f.write('<span style="font-size: %ipt">'  % fontsize)
                    elif print_rtf:
                        
                        f.write("\\fs%i " % (fontsize * 2,))
                    font_size = fontsize

                if style != newstyle:
                    if 0: #newstyle & 7 != 0:
                        pdb.set_trace()
                    bits = [2**i for i in range(1,8)]
                    stylecodes = ['sub','sup','out','ita','rev','bld','uln']
                    rtfcommands = (
                        ('\\nosupersub ', '\\sub '),
                        ('\\nosupersub ', '\\super '),
                        ('\\outl0\\strokewidth0 ', '\\outl\\strokewidth60 '),
                        ('\\i0 ', '\\i '),
                        ('{\\colortbl;\\red0\\green0\\blue0;\\red255\\green255\\blue255;}\\cb1\\cf2 ', '{\\colortbl;\\red0\\green0\\blue0;\\red255\\green255\\blue255;}\\cb2\\cf1 '),
                        ('\\b0 ', '\\b '),
                        ('\\ulnone ', '\\ul '))

                    rtfstyles = dict(zip(bits, rtfcommands))
                    print "oldstyle", bin(style)
                    print "newstyle", bin(newstyle)
                    # pdb.set_trace()

                    for bit in bits:
                        curr = newstyle & bit
                        old = style & bit
                    
                        if       curr and     old:
                            # no change
                            pass
                        elif not curr and not old:
                            # no change
                            pass
                        elif     curr and not old:
                            # switch on
                            if print_rtf:
                                f.write(rtfstyles[bit][1])
                        elif not curr and     old:
                            # switch off
                            if print_rtf:
                                f.write(rtfstyles[bit][0])
                    style = newstyle
                log.append("NEWCARDSET")
                j += 3
                continue
            elif nc == 8 or c == 24:
                j += 19
                bytes = [hex(ord(i)) for i in chain[j:j+10]]
                pp(bytes)
                pdb.set_trace()
                log.append("0x08 | 0x24")
                continue
            elif nc == 0xf5:
                j += 10
                log.append("0xF5")
                continue
            elif c in ('{','}'):
                if print_rtf:
                    f.write("\\%s" % c)
                if print_html:
                    f.write( c )
                log.append("{}")
                continue
            
            f.write(c)
            if log:
                if log[-1] != "CHARS":
                    log.append("CHARS")

        if kwlog:
            print "<<<New Page>>>"
        if print_rtf:
            f.write("}")
    f.close()

if __name__ == '__main__':
    main()



