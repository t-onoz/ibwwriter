try:
    import unittest2 as unittest
except ImportError:
    import unittest
try:
    from tempfile import TemporaryFile, TemporaryDirectory
except ImportError:
    from tempfile import TemporaryFile
    from backports.tempfile import TemporaryDirectory

import numpy as np

from igorwriter import IgorWave, validator, ENCODING


class WaveTestCase(unittest.TestCase):
    def test_datetime(self):
        array = np.arange(np.datetime64('2019-01-01'), np.datetime64('2019-12-31'), np.timedelta64(1, 'D'))
        wave = IgorWave(array)
        self.assertIs(wave._check_array().dtype.type, np.float64)
        with TemporaryFile('wb') as bin, TemporaryFile('wt') as text:
            wave.save(bin)
            wave.save_itx(text)

    def test_pint(self):
        import pint
        ureg = pint.UnitRegistry()
        Q = ureg.Quantity
        a = np.arange(0.0, 10.0, 1.0)
        with self.subTest('short units'):
            wave = IgorWave(Q(a, 's'))
            bunits = wave._wave_header.dataUnits
            expected = 's'.encode(ENCODING)
            self.assertEqual(bunits, expected)
        with self.subTest('long units'):
            q = Q(a, 'kg m / s**2')
            wave = IgorWave(q)
            bunits = wave._extended_data_units
            expected = '{:~}'.format(q.units).encode(ENCODING)
            self.assertEqual(bunits, expected)

    def test_file_io(self):
        array = np.random.randint(0, 100, 10, dtype=np.int32)
        wave = IgorWave(array)
        with TemporaryDirectory() as datadir:
            itx = datadir + '/wave0.itx'
            ibw = datadir + '/wave0.ibw'
            wave.save_itx(itx)
            with open(itx, 'w') as fp:
                wave.save_itx(fp)

            wave.save(ibw)
            with self.subTest('save in a new binary file'):
                with open(ibw, 'wb') as fp:
                    wave.save(fp)
            with self.subTest('append to a binary should fail'):
                with open(ibw, 'wb') as fp:
                    fp.write(b'something')
                    self.assertRaises(ValueError, wave.save, fp)
                with open(ibw, 'ab') as fp:
                    self.assertRaises(ValueError, wave.save, fp)
            with self.subTest('save in a truncated binary file'):
                with open(ibw, 'wb') as fp:
                    wave.save(fp)

    def test_array_type(self):
        valid_types = (np.bool_, np.float16, np.int32, np.uint32, np.int64, np.uint64, np.float32, np.float64, np.complex128)
        invalid_types = (object, str)
        for vt in valid_types:
            with self.subTest('type: %r' % vt):
                wave = IgorWave(np.random.randint(0, 100, 10).astype(vt))
                with TemporaryFile('wb') as fp:
                    wave.save(fp)
                with TemporaryFile('wt') as fp:
                    wave.save_itx(fp)
        for it in invalid_types:
            with self.subTest('type: %r' % it):
                wave = IgorWave(np.random.randint(0, 100, 10).astype(it))
                with TemporaryFile('wb') as fp:
                    self.assertRaises(TypeError, wave.save, fp)
                with TemporaryFile('wt') as fp:
                    self.assertRaises(TypeError, wave.save_itx, fp)

    def test_dimscale(self):
        array = np.random.randint(0, 100, 10, dtype=np.int32)
        wave = IgorWave(array)
        wave.set_dimscale('x', 0, 0.01, 's')
        with TemporaryFile('wb') as fp:
            wave.save(fp)
        with TemporaryFile('wt') as fp:
            wave.save_itx(fp)

    def test_data_units(self):
        wavename = 'wave0'
        unitslist = ('', 'sec', 'second')
        descs = ('empty units', 'short units', 'long units')
        for desc, units in zip(descs, unitslist):
            with self.subTest(desc):
                com = 'X SetScale d,.*"%s",.*\'%s\'' % (units, wavename)
                array = np.random.randint(0, 100, 10, dtype=np.int32)
                wave = IgorWave(array)
                wave.set_datascale(units)
                with TemporaryFile('wb') as fp:
                    wave.save(fp)
                with TemporaryFile('w+t') as fp:
                    wave.save_itx(fp)
                    fp.seek(0)
                    content = fp.read()
                    self.assertRegex(content, com)

    def test_dim_units(self):
        wavename = 'wave0'
        unitslist = ('', 'sec', 'second')
        descs = ('empty units', 'short units', 'long units')
        for desc, units in zip(descs, unitslist):
            with self.subTest(desc):
                com = 'X SetScale /P [xyzt],.*"%s",.*\'%s\'' % (units, wavename)
                array = np.random.randint(0, 100, 10, dtype=np.int32)
                wave = IgorWave(array)
                wave.set_dimscale('x', 0, 1, units)
                with TemporaryFile('wb') as fp:
                    wave.save(fp)
                with TemporaryFile('w+t') as fp:
                    wave.save_itx(fp)
                    fp.seek(0)
                    content = fp.read()
                    self.assertRegex(content, com)

    def test_invalid_name(self):
        name = '\'invalid_name\''  # wave cannot contain quotation marks
        array = np.random.randint(0, 100, 10, dtype=np.int32)
        wave = IgorWave(array)
        self.assertRaises(validator.InvalidNameError, wave.rename, name, on_errors='raise')
        wave.rename(name, on_errors='fix')
        self.assertEqual(wave.name, name.replace('\'', '_'))


if __name__ == '__main__':
    unittest.main()
