import tempfile
import unittest
from pathlib import Path
import numpy as np
from core import Store, Matcher, Trigger, NEUTRAL, discover

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.store = Store(self.path/'reactions.json')

    def add(self,key,value):
        self.store.add(key,np.full((12,10),value))

    def test_roundtrip_and_independent_retraining(self):
        self.add('one.JPG',.8)
        self.add('two.mov',.4)
        self.add('one.JPG',.75)
        self.store.delete('one.JPG',0)
        loaded = Store(self.store.path)
        self.assertEqual(len(loaded.data['samples']['one.JPG']),1)
        self.assertEqual(len(loaded.data['samples']['two.mov']),1)

    def test_reject_neutral_unknown_and_ambiguity(self):
        self.add(NEUTRAL,0.)
        self.add('one.JPG',.8)
        match = Matcher(self.store)
        self.assertEqual(match.predict(np.full(10,.79))[0],'one.JPG')
        self.assertIsNone(match.predict(np.zeros(10))[0])
        self.assertIsNone(match.predict(np.full(10,2.))[0])
        self.add('two.mov',.8)
        self.assertIsNone(match.predict(np.full(10,.8))[0])

    def test_requires_neutral_and_ignores_deleted_files(self):
        self.add('one.JPG',.8)
        self.assertIsNone(Matcher(self.store).predict(np.full(10,.8))[0])
        self.add(NEUTRAL,0)
        self.assertIsNone(Matcher(self.store,keys=[]).predict(np.full(10,.8))[0])

    def test_trigger_stability_rearm_switch(self):
        t = Trigger()
        self.assertIsNone(t.update('a',0))
        self.assertEqual(t.update('a',.5),'a')
        self.assertIsNone(t.update('a',5))
        t.update(None,5.1)
        t.update(None,6)
        t.update('a',6.1)
        self.assertEqual(t.update('a',6.7),'a')
        t.update('b',6.8)
        self.assertIsNone(t.update('b',7.4))
        self.assertEqual(t.update('b',8.4),'b')

    def test_jitter_never_triggers(self):
        t = Trigger()
        for i in range(40):
            self.assertIsNone(t.update('a' if i%2 else 'b',i*.1))

    def test_discovery_relative_ids_and_extensions(self):
        (self.path/'sub').mkdir()
        for name in ['a.JPG','b.MOV','sub/a.JPG','ignore.txt']:
            (self.path/name).touch()
        self.assertEqual(set(discover(self.path)),{'a.JPG','b.MOV','sub/a.JPG'})

    def test_corrupt_and_short_recording(self):
        with self.assertRaises(ValueError):
            self.store.add('a',[[0]]*3)
        with self.assertRaises(ValueError):
            self.store.add('a',[[float('nan')]]*10)

if __name__ == '__main__':
    unittest.main()
