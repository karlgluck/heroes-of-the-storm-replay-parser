# Copyright (c) 2013 Blizzard Entertainment
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import struct
import base64

# A note on decoding blobs:
#
# The library Blizzard wrote has no distinction between strings and binary blobs
# at the protocol level. Because the results are going to be formatted as JSON
# and printed in utf-8 text, they must be properly encoded.
#
# I extended their decoders to support distinguishing these binary blobs. Every
# blob will now return a dictionary instead of a string. This dictionary will
# contain one or two members:
#   * 'utf8' - A utf-8 decoded Unicode string representing the blob,
#              created using Python's 'replace' option. This is what you expect
#              a string to be.
#   * 'base64' - A base-64 encoded version of the bytes from the blob. This member
#                is present if and only if the blob cannot be decoded correctly
#                into the utf8 member.
#
# This distinction is necessary because one cannot simply interpret all blobs
# as base64, since strings would be unrecognizable, or as utf-8 Unicode, since
# not all byte sequences form valid Unicode strings. This makes it easy to use
# the most common case of just getting strings from the replay, but keeps it
# possible to obtain the original binary blob by first checking for the base64
# member, then decoding either it or utf8.
    

class TruncatedError(Exception):
    pass


class CorruptedError(Exception):
    pass


class BitPackedBuffer:
    def __init__(self, contents, endian='big'):
        self._data = contents or []
        self._used = 0
        self._next = None
        self._nextbits = 0
        self._bigendian = (endian == 'big')

    def __str__(self):
        return 'buffer(%02x/%d,[%d]=%s)' % (
            self._nextbits and self._next or 0, self._nextbits,
            self._used, '%02x' % (ord(self._data[self._used]),) if (self._used < len(self._data)) else '--')

    def copy(self, other):
        self._data = other._data
        self._used = other._used
        self._next = other._next
        self._nextbits = other._nextbits
        self._bigendian = other._bigendian

    def peek_bytes_as_hex_string(self, bytes=0):
        if bytes == 0:
            bytes = len(self._data)
        bpb = BitPackedBuffer([], self._bigendian)
        bpb.copy(self)
        return ''.join('{:02x}'.format(ord(x)) for x in bpb.read_unaligned_bytes(bytes))

    def peek_bytes_as_bin_string(self, bytes=0):
        if bytes == 0:
            bytes = len(self._data)
        bpb = BitPackedBuffer([], self._bigendian)
        bpb.copy(self)
        return ''.join('{:08b}'.format(ord(x)) for x in bpb.read_unaligned_bytes(bytes))

    def peek_bits_as_bin_string(self, bits=0):
        if bits == 0:
            bits = len(self._data) * 8
        bpb = BitPackedBuffer([], self._bigendian)
        bpb.copy(self)
        return ('{:0%ib}'%bits).format(bpb.read_bits(bits))

    def done(self):
        return self._nextbits == 0 and self._used >= len(self._data)

    def used_bits(self):
        return self._used * 8 - self._nextbits

    def byte_align(self):
        self._nextbits = 0

    def read_aligned_bytes(self, bytes):
        self.byte_align()
        data = self._data[self._used:self._used + bytes]
        self._used += bytes
        if len(data) != bytes:
            raise TruncatedError(self)
        return data

    def state(self):
        return '{next=%i,nextbits=%i,used=%i}' % (self._next, self._nextbits, self._used)

    def read_bits(self, bits):
        result = 0
        resultbits = 0
        while resultbits != bits:
            if self._nextbits == 0:
                if self.done():
                    raise TruncatedError(self)
                self._next = ord(self._data[self._used])
                self._used += 1
                self._nextbits = 8
            copybits = min(bits - resultbits, self._nextbits)
            copy = (self._next & ((1 << copybits) - 1))
            if self._bigendian:
                result |= copy << (bits - resultbits - copybits)
            else:
                result |= copy << resultbits
            self._next >>= copybits
            self._nextbits -= copybits
            resultbits += copybits
        return result

    def read_unaligned_bytes(self, bytes):
        return ''.join([chr(self.read_bits(8)) for i in xrange(bytes)])


class BitPackedDecoder:
    def __init__(self, contents, typeinfos):
        self._buffer = BitPackedBuffer(contents)
        self._typeinfos = typeinfos

    def __str__(self):
        return self._buffer.__str__()

    def instance(self, typeid):
        if typeid >= len(self._typeinfos):
            raise CorruptedError(self)
        typeinfo = self._typeinfos[typeid]
        return getattr(self, typeinfo[0])(*typeinfo[1])

    def byte_align(self):
        self._buffer.byte_align()

    def done(self):
        return self._buffer.done()

    def used_bits(self):
        return self._buffer.used_bits()

    def _array(self, bounds, typeid):
        length = self._int(bounds)
        return [self.instance(typeid) for i in xrange(length)]

    def _bitarray(self, bounds):
        length = self._int(bounds)
        return (length, self._buffer.read_bits(length))

    def _blob(self, bounds):
        length = self._int(bounds)
        result = self._buffer.read_aligned_bytes(length)
        try:
            result = {'utf8': result.decode('utf-8', 'strict')}
        except UnicodeDecodeError:
            result = {
                'utf8': result.decode('utf-8', 'replace'),
                'base64': base64.b64encode(result)
            }
        return result

    def _bool(self):
        return self._int((0, 1)) != 0

    def _choice(self, bounds, fields):
        tag = self._int(bounds)
        if tag not in fields:
            raise CorruptedError(self)
        field = fields[tag]
        return {field[0]: self.instance(field[1])}

    def _fourcc(self):
        return self._buffer.read_unaligned_bytes(4)

    def _int(self, bounds):
        return bounds[0] + self._buffer.read_bits(bounds[1])

    def _null(self):
        return None

    def _optional(self, typeid):
        exists = self._bool()
        return self.instance(typeid) if exists else None

    def _real32(self):
        return struct.unpack('>f', self._buffer.read_unaligned_bytes(4))

    def _real64(self):
        return struct.unpack('>d', self._buffer.read_unaligned_bytes(8))

    def _struct(self, fields):
        result = {}
        for field in fields:
            if field[0] == '__parent':
                parent = self.instance(field[1])
                if isinstance(parent, dict):
                    result.update(parent)
                elif len(fields) == 1:
                    result = parent
                else:
                    result[field[0]] = parent
            else:
                result[field[0]] = self.instance(field[1])
        return result




class BitPackedDecoderDebug:
    def __init__(self, contents, typeinfos):
        self._buffer = BitPackedBuffer(contents)
        self._typeinfos = typeinfos
        self._markers = []
        self._json = {}

    def __str__(self):
        return self._buffer.__str__()

    def peek_bytes_as_hex_string(self, bytes):
        return self._buffer.peek_bytes_as_hex_string(bytes)

    def peek_bytes_as_bin_string(self, bytes=0):
        return self._buffer.peek_bytes_as_bin_string(bytes)

    def space_binary_string_by_markers(self, bin_string, first_bit_index):
        retval = ''
        x = 0
        while x < len(bin_string):
            for m in self._markers:
                if m['at'] == (first_bit_index + x):
                    retval = retval + '{' + m['type'] + '}'
            retval = retval + bin_string[x]
            x += 1
        for m in self._markers:
            if m['at'] == (first_bit_index + x):
                retval = retval + '{' + m['type'] + '}'
        return retval

    def get_json_and_reset(self):
        retval = self._json
        self._json = {}
        return retval

    def instance(self, typeid):
        used_bits = self._buffer.used_bits()
        self._markers.append({'at':self.used_bits(),'type':'instance(%i)'%typeid})
        old_json = self._json
        self._json = {'bit_start': self.used_bits(), 'typeid': typeid}
        if typeid >= len(self._typeinfos):
            return {"ERROR":"Asked to instance typeid '%i' but there are only '%i' type IDs" % (typeid, len(self._typeinfos)), "hex": hex_string }
        typeinfo = self._typeinfos[typeid]
        retval = getattr(self, typeinfo[0])(*typeinfo[1])
        self._json['bit_end']  = self.used_bits()
        old_json['instance%i'%self.used_bits()] = self._json
        self._json = old_json
        self._markers.append({'at':self.used_bits(),'type':'end-instance(%i)'%typeid})
        return retval

    def byte_align(self):
        self._buffer.byte_align()

    def done(self):
        return self._buffer.done()

    def used_bits(self):
        return self._buffer.used_bits()

    def _array(self, bounds, typeid):
        self._markers.append({'at':self.used_bits(),'type':'array(%s,%s)'%(str(bounds),str(typeid))})
        old_json = self._json
        self._json = {'bit_start': self.used_bits(), 'bounds': bounds, 'typeid': typeid}
        length = self._int(bounds)
        self._json['length'] = length
        retval = [self.instance(typeid) for i in xrange(length)]
        old_json['array%i' % self.used_bits()] = self._json
        self._json = old_json
        return retval

    def _bitarray(self, bounds):
        self._markers.append({'at':self.used_bits(),'type':'bitarray(%s)'%str(bounds)})
        old_json = self._json
        self._json = {'bit_start': self.used_bits(), 'bounds': bounds}
        length = self._int(bounds)
        self._json['bits'] = self._buffer.peek_bits_as_bin_string(length)
        retval = (length, self._buffer.read_bits(length))
        old_json['bitarray%i'%self.used_bits()] = self._json
        self._json = old_json
        return retval

    def _blob(self, bounds):
        self._markers.append({'at':self.used_bits(),'type':'blob(%s)'%str(bounds)})
        old_json = self._json
        self._json = {'bit_start': self.used_bits(), 'bounds': bounds}
        length = self._int(bounds)
        self._json['length'] = length
        retval = self._buffer.read_aligned_bytes(length)
        self._json['bytes'] = ''.join('{:02x}'.format(ord(x)) for x in retval)
        old_json['blob%i'%self.used_bits()] = self._json
        self._json = old_json
        try:
            retval = {'utf8': retval.decode('utf-8', 'strict')}
        except UnicodeDecodeError:
            retval = {
                'utf8': retval.decode('utf-8', 'replace'),
                'base64': base64.b64encode(retval)
            }
        return retval

    def _bool(self):
        old_json = self._json
        self._json = {'bit_start': self.used_bits()}
        self._markers.append({'at':self.used_bits(),'type':'bool'})
        retval = self._int((0, 1)) != 0
        self._json['value'] = retval
        old_json['bool%i'%self.used_bits()] = self._json
        self._json = old_json
        return retval

    def _choice(self, bounds, fields):
        self._markers.append({'at':self.used_bits(),'type':'choice(%s,%s)'%(str(bounds),str(fields))})
        old_json = self._json
        self._json = {'bit_start': self.used_bits(), 'bounds': bounds, 'fields':fields}
        tag = self._int(bounds)
        if tag not in fields:
            return {"ERROR":"Choice '%s' does not exist in available fields '%s'" % (str(tag), str(fields))}
        field = fields[tag]
        retval = {field[0]: self.instance(field[1])}
        self._json['value'] = retval
        old_json['choice%i'%self.used_bits()] = self._json
        self._json = old_json
        return retval

    def _fourcc(self):
        old_json = self._json
        self._json = {'bit_start': self.used_bits()}
        self._markers.append({'at':self.used_bits(),'type':'blob'})
        retval = self._buffer.read_unaligned_bytes(4)
        old_json['fourcc%i'%self.used_bits()] = self._json
        self._json = old_json
        return retval

    def _int(self, bounds):
        old_json = self._json
        self._json = {'bit_start': self.used_bits(), 'bounds': bounds, 'bits':self._buffer.peek_bits_as_bin_string(bounds[1])}
        bitpos = self.used_bits()
        retval = bounds[0] + self._buffer.read_bits(bounds[1])
        self._markers.append({'at':bitpos,'type':'int(%s)=%i @ %s'%(str(bounds), retval, self._buffer.state())})
        self._json['value'] = retval
        old_json['int%i'%self.used_bits()] = self._json
        self._json = old_json
        return retval

    def _null(self):
        self._markers.append({'at':self.used_bits(),'type':'null'})
        return None

    def _optional(self, typeid):
        old_json = self._json
        self._json = {'bit_start': self.used_bits(), 'typeid':typeid}
        self._markers.append({'at':self.used_bits(),'type':'optional(%s)'%str(typeid)})
        exists = self._bool()
        retval = self.instance(typeid) if exists else None
        old_json['optional%i'%self.used_bits()] = self._json
        self._json = old_json
        return retval

    def _real32(self):
        old_json = self._json
        self._json = {'bit_start': self.used_bits()}
        self._markers.append({'at':self.used_bits(),'type':'real32'})
        retval = struct.unpack('>f', self._buffer.read_unaligned_bytes(4))
        self._json['value'] = retval
        old_json['real32%i'%self.used_bits()] = self._json
        self._json = old_json
        return retval

    def _real64(self):
        old_json = self._json
        self._json = {'bit_start': self.used_bits()}
        self._markers.append({'at':self.used_bits(),'type':'real64'})
        retval = struct.unpack('>d', self._buffer.read_unaligned_bytes(8))
        self._json['value'] = retval
        old_json['real64%i'%self.used_bits()] = self._json
        self._json = old_json
        return retval

    def _struct(self, fields):
        old_json = self._json
        self._json = {'bit_start': self.used_bits(), 'fields': fields}
        self._markers.append({'at':self.used_bits(),'type':'struct(%s)'%str(fields)})
        result = {}
        for field in fields:
            if field[0] == '__parent':
                parent = self.instance(field[1])
                if isinstance(parent, dict):
                    result.update(parent)
                elif len(fields) == 1:
                    result = parent
                else:
                    result[field[0]] = parent
            else:
                result[field[0]] = self.instance(field[1])
        old_json['struct%i'%self.used_bits()] = self._json
        self._json = old_json
        return result




class VersionedDecoder:
    def __init__(self, contents, typeinfos):
        self._buffer = BitPackedBuffer(contents)
        self._typeinfos = typeinfos

    def __str__(self):
        return self._buffer.__str__()

    def instance(self, typeid):
        if typeid >= len(self._typeinfos):
            raise CorruptedError(self)
        typeinfo = self._typeinfos[typeid]
        return getattr(self, typeinfo[0])(*typeinfo[1])

    def byte_align(self):
        self._buffer.byte_align()

    def done(self):
        return self._buffer.done()

    def used_bits(self):
        return self._buffer.used_bits()

    def _expect_skip(self, expected):
        if self._buffer.read_bits(8) != expected:
            raise CorruptedError(self)

    def _vint(self):
        b = self._buffer.read_bits(8)
        negative = b & 1
        result = (b >> 1) & 0x3f
        bits = 6
        while (b & 0x80) != 0:
            b = self._buffer.read_bits(8)
            result |= (b & 0x7f) << bits
            bits += 7
        return -result if negative else result

    def _array(self, bounds, typeid):
        self._expect_skip(0)
        length = self._vint()
        return [self.instance(typeid) for i in xrange(length)]

    def _bitarray(self, bounds):
        self._expect_skip(1)
        length = self._vint()
        return (length, self._buffer.read_aligned_bytes((length + 7) / 8))

    def _blob(self, bounds):
        self._expect_skip(2)
        length = self._vint()
        result = self._buffer.read_aligned_bytes(length)
        try:
            result = {'utf8': result.decode('utf-8', 'strict')}
        except UnicodeDecodeError:
            result = {
                'utf8': result.decode('utf-8', 'replace'),
                'base64': base64.b64encode(result)
            }
        return result

    def _bool(self):
        self._expect_skip(6)
        return self._buffer.read_bits(8) != 0

    def _choice(self, bounds, fields):
        self._expect_skip(3)
        tag = self._vint()
        if tag not in fields:
            self._skip_instance()
            return {}
        field = fields[tag]
        return {field[0]: self.instance(field[1])}

    def _fourcc(self):
        self._expect_skip(7)
        return self._buffer.read_aligned_bytes(4)

    def _int(self, bounds):
        self._expect_skip(9)
        return self._vint()

    def _null(self):
        return None

    def _optional(self, typeid):
        self._expect_skip(4)
        exists = self._buffer.read_bits(8) != 0
        return self.instance(typeid) if exists else None

    def _real32(self):
        self._expect_skip(7)
        return struct.unpack('>f', self._buffer.read_aligned_bytes(4))

    def _real64(self):
        self._expect_skip(8)
        return struct.unpack('>d', self._buffer.read_aligned_bytes(8))

    def _struct(self, fields):
        self._expect_skip(5)
        result = {}
        length = self._vint()
        for i in xrange(length):
            tag = self._vint()
            field = next((f for f in fields if f[2] == tag), None)
            if field:
                if field[0] == '__parent':
                    parent = self.instance(field[1])
                    if isinstance(parent, dict):
                        result.update(parent)
                    elif len(fields) == 1:
                        result = parent
                    else:
                        result[field[0]] = parent
                else:
                    result[field[0]] = self.instance(field[1])
            else:
                self._skip_instance()
        return result

    def _skip_instance(self):
        skip = self._buffer.read_bits(8)
        if skip == 0:  # array
            length = self._vint()
            for i in xrange(length):
                self._skip_instance()
        elif skip == 1:  # bitblob
            length = self._vint()
            self._buffer.read_aligned_bytes((length + 7) / 8)
        elif skip == 2:  # blob
            length = self._vint()
            self._buffer.read_aligned_bytes(length)
        elif skip == 3:  # choice
            tag = self._vint()
            self._skip_instance()
        elif skip == 4:  # optional
            exists = self._buffer.read_bits(8) != 0
            if exists:
                self._skip_instance()
        elif skip == 5:  # struct
            length = self._vint()
            for i in xrange(length):
                tag = self._vint()
                self._skip_instance()
        elif skip == 6:  # u8
            self._buffer.read_aligned_bytes(1)
        elif skip == 7:  # u32
            self._buffer.read_aligned_bytes(4)
        elif skip == 8:  # u64
            self._buffer.read_aligned_bytes(8)
        elif skip == 9:  # vint
            self._vint()




