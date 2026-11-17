"""Small offline smoke tests. These do not validate external DART API responses."""
import hashlib
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

import collector
import complete_track2_b
import refine_track2_b
import refine_track2_b_p1


class SmokeTests(unittest.TestCase):
    def test_number_with_thousands_separator(self):
        self.assertEqual(collector.number('1,234.50'), Decimal('1234.50'))

    def test_parenthesized_negative(self):
        self.assertEqual(collector.number('(9,000)'), Decimal('-9000'))

    def test_dash_is_not_zero(self):
        with self.assertRaises(ValueError):
            collector.number('-')

    def test_table_parser_coordinates(self):
        p = collector.Tables()
        p.feed('<table><tr><th rowspan="2">항목</th><th>금액</th></tr>'
               '<tr><td>1,000</td></tr></table>')
        grid = collector.grid(p.tables[0]['rows'])
        self.assertEqual(grid, [['항목', '금액'], ['항목', '1,000']])

    def test_hash_preserved_in_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = collector.Store(Path(tmp))
            try:
                payload = b'<xml>synthetic-only</xml>'
                store.persist('sample', 'demo', {}, payload)
                row = store.get('sample')
                self.assertEqual(store.verify(row), payload)
                self.assertEqual(row['digest'], hashlib.sha256(payload).hexdigest())
            finally:
                store.db.close()

    def test_period_meta_quarter(self):
        t = {'fiscal_period': '2025-03', 'member': 'synthetic', 'table_index': 0}
        meta, evidence = refine_track2_b.period_meta(
            t, 1, [['항목', '당기']], {}, 'flow')
        self.assertEqual(meta['period_start'], '2025-01-01')
        self.assertEqual(meta['period_end'], '2025-03-31')
        self.assertEqual(meta['value_kind'], 'quarter')
        self.assertEqual(evidence, [])

    def test_annual_col_mapping(self):
        self.assertEqual(refine_track2_b_p1.yearcols(['항목', '2025년', '2024년'], 2025),
                         {1: 2025, 2: 2024})

    def test_aging_schema(self):
        t = {'grid': [
            ['항목','3개월 이하','3~6개월','6~12개월','1년 초과','합계'],
            ['매출채권','1','2','3','4','10'],
        ]}
        self.assertEqual(complete_track2_b.age_schema(t), 1)


if __name__ == '__main__':
    unittest.main()
