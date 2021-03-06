#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from odps.tests.core import TestBase
from odps.compat import unittest
from odps.models import Schema
from odps.df.types import validate_data_type
from odps.df.expr.tests.core import MockTable
from odps.df.expr.expressions import *
from odps.df.expr.element import *


class Test(TestBase):
    def setup(self):
        datatypes = lambda *types: [validate_data_type(t) for t in types]
        schema = Schema.from_lists(['name', 'id', 'fid', 'isMale', 'scale', 'birth'],
                                   datatypes('string', 'int64', 'float64', 'boolean', 'decimal', 'datetime'))
        table = MockTable(name='pyodps_test_expr_table', schema=schema)

        self.expr = CollectionExpr(_source_data=table, _schema=schema)

    # def testCacheNode(self):
    #     self.assertIs(self.expr.fid.isnull(), self.expr.fid.isnull())
    #     self.assertIs(self.expr.name.fillna('test'), self.expr.name.fillna('test'))
    #     self.assertIs(self.expr.id.cut([5, 10], labels=['mid']),
    #                   self.expr.id.cut([5, 10], labels=['mid']))
    #
    #     s = self.expr.id.notnull()
    #     s._cache_data = [4, ]
    #     self.assertEqual(self.expr.id.notnull()._cache_data, [4, ])
    #     self.expr.id.optimize_banned = True
    #     self.assertTrue(self.expr.id.optimize_banned)

    def testIsNull(self):
        self.assertIsInstance(self.expr.fid.isnull(), IsNull)
        self.assertIsInstance(self.expr.fid.isnull(), BooleanSequenceExpr)
        self.assertIsInstance(self.expr.fid.sum().isnull(), BooleanScalar)

    def testNotNull(self):
        self.assertIsInstance(self.expr.fid.notnull(), NotNull)
        self.assertIsInstance(self.expr.fid.notnull(), BooleanSequenceExpr)
        self.assertIsInstance(self.expr.fid.sum().notnull(), BooleanScalar)

    def testFillNa(self):
        self.assertIsInstance(self.expr.name.fillna('test'), FillNa)
        self.assertIsInstance(self.expr.name.fillna('test'), StringSequenceExpr)
        self.assertIsInstance(self.expr.name.sum().fillna('test'), StringScalar)

        self.assertRaises(ValueError, lambda: self.expr.id.fillna('abc'))

    def testIsIn(self):
        expr = self.expr.name.isin(list('abc'))
        self.assertIsInstance(expr, IsIn)
        self.assertEqual(len(expr.values), 3)
        self.assertEqual([it.value for it in expr.values], list('abc'))
        self.assertIsInstance(self.expr.name.isin(list('abc')), BooleanSequenceExpr)
        self.assertIsInstance(self.expr.name.sum().isin(list('abc')), BooleanScalar)

    def testBetween(self):
        self.assertIsInstance(self.expr.id.between(1, 3), Between)
        self.assertIsInstance(self.expr.name.between(1, 3), BooleanSequenceExpr)
        self.assertIsInstance(self.expr.name.sum().between(1, 3), BooleanScalar)

    def testIfElse(self):
        self.assertIsInstance(
                (self.expr.id == 3).ifelse(self.expr.id, self.expr.fid), IfElse)
        self.assertIsInstance(
                (self.expr.id == 3).ifelse(self.expr.id, self.expr.fid), Float64SequenceExpr)
        self.assertIsInstance(
                (self.expr.id == 3).ifelse(self.expr.id.sum(), self.expr.fid), Float64SequenceExpr)

    def testSwitch(self):
        expr = self.expr.id.switch(3, self.expr.name, self.expr.fid.abs(), self.expr.name + 'test')
        self.assertIsInstance(expr, Switch)
        self.assertEqual(len(expr.conditions), 2)
        self.assertEqual(len(expr.thens), 2)
        self.assertIsInstance(expr, StringSequenceExpr)
        self.assertNotIsInstance(expr, Scalar)

        expr = self.expr.id.switch((3, self.expr.name), (self.expr.fid.abs(), self.expr.name + 'test'))
        self.assertIsInstance(expr, Switch)
        self.assertEqual(len(expr.conditions), 2)
        self.assertEqual(len(expr.thens), 2)
        self.assertIsInstance(expr, StringSequenceExpr)
        self.assertNotIsInstance(expr, Scalar)

        expr = self.expr.id.switch(3, self.expr.name, self.expr.fid.abs(), self.expr.name + 'test',
                                   default=self.expr.name.lower())
        self.assertIsInstance(expr, Switch)
        self.assertEqual(len(expr.conditions), 2)
        self.assertEqual(len(expr.thens), 2)
        self.assertIsInstance(expr.default, StringSequenceExpr)
        self.assertIsInstance(expr, StringSequenceExpr)
        self.assertNotIsInstance(expr, Scalar)

        self.assertRaises(ExpressionError, lambda: self.expr.switch(3, self.expr.name))

        expr = self.expr.switch(self.expr.id == 3, self.expr.name,
                                self.expr.id == 2, self.expr.name + 'test')
        self.assertIsInstance(expr, Switch)
        self.assertEqual(len(expr.conditions), 2)
        self.assertEqual(len(expr.thens), 2)
        self.assertIsInstance(expr, StringSequenceExpr)
        self.assertNotIsInstance(expr, Scalar)

    def testCut(self):
        expr = self.expr.id.cut([5, 10], labels=['mid'])
        self.assertIsInstance(expr, Cut)
        self.assertIsInstance(expr, StringSequenceExpr)

        expr = self.expr.id.max().cut([5, 10], labels=['mid'])
        self.assertIsInstance(expr, Cut)
        self.assertIsInstance(expr, StringScalar)

        self.assertRaises(ValueError, lambda: self.expr.id.cut([5]))
        self.assertRaises(ValueError, lambda: self.expr.id.cut([5], include_under=True))
        self.assertRaises(ValueError, lambda: self.expr.id.cut([5], include_over=True))

    def testReduceApply(self):
        expr = self.expr[self.expr.id, self.expr['name', 'id'].apply(
            lambda row: row.name + row.id, axis=1, reduce=True).rename('nameid')]

        self.assertIsInstance(expr._fields[1], MappedExpr)


if __name__ == '__main__':
    unittest.main()