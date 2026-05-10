/**
 * Tests for expressionEval.js. Run with `node --test src/expressionEval.test.js`.
 *
 * Mirrors backend/tests/test_expression_eval.py to keep the JS and Python
 * evaluators behaviourally aligned.
 */

import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import { evaluateExpression } from './expressionEval.js'

describe('arithmetic', () => {
  it('handles addition', () => assert.equal(evaluateExpression('1 + 2', {}), 3))
  it('handles subtraction', () => assert.equal(evaluateExpression('10 - 4', {}), 6))
  it('handles multiplication', () => assert.equal(evaluateExpression('3 * 4', {}), 12))
  it('handles division', () => assert.equal(evaluateExpression('10 / 4', {}), 2.5))
  it('handles 10/3 with full precision', () => {
    const result = evaluateExpression('10 / 3', {})
    assert.ok(result !== null)
    assert.ok(Math.abs(result - 10 / 3) < 1e-9)
  })

  it('respects operator precedence', () => {
    assert.equal(evaluateExpression('2 + 3 * 4', {}), 14)
    assert.equal(evaluateExpression('(2 + 3) * 4', {}), 20)
    assert.equal(evaluateExpression('20 / 4 / 5', {}), 1)
  })

  it('handles unary negation', () => {
    assert.equal(evaluateExpression('-5', {}), -5)
    assert.equal(evaluateExpression('-(2 + 3)', {}), -5)
    assert.equal(evaluateExpression('10 + -3', {}), 7)
  })

  it('handles decimal literals', () => {
    assert.equal(evaluateExpression('0.2', {}), 0.2)
    assert.equal(evaluateExpression('.5 + .5', {}), 1)
    assert.equal(evaluateExpression('100 * 0.2', {}), 20)
  })
})

describe('field references', () => {
  it('resolves a top-level field value', () => {
    assert.equal(evaluateExpression('price', { price: 42 }), 42)
  })

  it('treats missing fields as 0', () => {
    assert.equal(evaluateExpression('price', {}), 0)
  })

  it('coerces numeric strings', () => {
    assert.equal(evaluateExpression('price * 2', { price: '10.5' }), 21)
  })

  it('treats non-numeric values as 0', () => {
    assert.equal(evaluateExpression('price + 5', { price: 'abc' }), 5)
  })

  it('supports cross-field arithmetic', () => {
    const data = { subtotal: 100, vat_amount: 20 }
    assert.equal(evaluateExpression('subtotal + vat_amount', data), 120)
  })
})

describe('repeat group references and aggregates', () => {
  it('sum() over repeat group field', () => {
    const data = { items: [{ price: 10 }, { price: 20 }] }
    assert.equal(evaluateExpression('sum(items.price)', data), 30)
  })

  it('count() over repeat group field', () => {
    const data = { items: [{ price: 10 }, { price: 20 }, { price: 30 }] }
    assert.equal(evaluateExpression('count(items.price)', data), 3)
  })

  it('count() over the repeat group itself', () => {
    const data = { items: [{ price: 10 }, { price: 20 }, { price: 30 }] }
    assert.equal(evaluateExpression('count(items)', data), 3)
  })

  it('avg() over repeat group field', () => {
    const data = { items: [{ score: 10 }, { score: 20 }, { score: 30 }] }
    assert.equal(evaluateExpression('avg(items.score)', data), 20)
  })

  it('min() over repeat group field', () => {
    const data = { items: [{ v: 7 }, { v: 3 }, { v: 9 }] }
    assert.equal(evaluateExpression('min(items.v)', data), 3)
  })

  it('max() over repeat group field', () => {
    const data = { items: [{ v: 7 }, { v: 3 }, { v: 9 }] }
    assert.equal(evaluateExpression('max(items.v)', data), 9)
  })
})

describe('element-wise arithmetic on arrays', () => {
  it('multiplies two array fields element-wise', () => {
    const data = {
      items: [
        { quantity: 2, unit_price: 5 },
        { quantity: 3, unit_price: 4 },
      ],
    }
    // (2*5) + (3*4) = 22
    assert.equal(evaluateExpression('sum(items.quantity * items.unit_price)', data), 22)
  })

  it('multiplies an array by a scalar', () => {
    const data = { items: [{ price: 10 }, { price: 20 }] }
    assert.equal(evaluateExpression('sum(items.price * 2)', data), 60)
  })

  it('subtracts two array fields element-wise', () => {
    const data = {
      items: [
        { gross: 100, discount: 10 },
        { gross: 50, discount: 5 },
      ],
    }
    assert.equal(evaluateExpression('sum(items.gross - items.discount)', data), 135)
  })
})

describe('nested expressions', () => {
  it('aggregate followed by scalar arithmetic', () => {
    const data = { items: [{ subtotal: 100 }, { subtotal: 50 }] }
    assert.equal(evaluateExpression('sum(items.subtotal) * 0.2', data), 30)
  })

  it('combines a top-level field with an aggregate', () => {
    const data = { subtotal: 100, items: [{ price: 10 }, { price: 20 }] }
    assert.equal(evaluateExpression('subtotal + sum(items.price)', data), 130)
  })
})

describe('edge cases', () => {
  it('aggregates over empty arrays return 0', () => {
    const data = { items: [] }
    assert.equal(evaluateExpression('sum(items.price)', data), 0)
    assert.equal(evaluateExpression('avg(items.price)', data), 0)
    assert.equal(evaluateExpression('min(items.price)', data), 0)
    assert.equal(evaluateExpression('max(items.price)', data), 0)
    assert.equal(evaluateExpression('count(items.price)', data), 0)
  })

  it('missing repeat group is treated as empty', () => {
    assert.equal(evaluateExpression('sum(items.price)', {}), 0)
    assert.equal(evaluateExpression('count(items)', {}), 0)
  })

  it('division by zero returns 0', () => {
    assert.equal(evaluateExpression('10 / 0', {}), 0)
    assert.equal(evaluateExpression('10 / x', {}), 0)
    assert.equal(evaluateExpression('10 / x', { x: 0 }), 0)
  })

  it('missing nested fields are treated as 0', () => {
    const data = { items: [{ price: 10 }, {}, { price: 20 }] }
    assert.equal(evaluateExpression('sum(items.price)', data), 30)
  })

  it('invalid expressions return null', () => {
    assert.equal(evaluateExpression('1 +', {}), null)
    assert.equal(evaluateExpression('(', {}), null)
    assert.equal(evaluateExpression('foo(bar)', {}), null) // unknown function
  })

  it('empty/blank expressions return null', () => {
    assert.equal(evaluateExpression('', {}), null)
    assert.equal(evaluateExpression('   ', {}), null)
  })

  it('non-object data is treated as empty', () => {
    assert.equal(evaluateExpression('price', null), 0)
    assert.equal(evaluateExpression('price', undefined), 0)
  })

  it('top-level array reference collapses to its sum', () => {
    const data = { items: [{ price: 10 }, { price: 20 }] }
    assert.equal(evaluateExpression('items.price', data), 30)
  })

  it('negation of an array negates each element', () => {
    const data = { items: [{ v: 1 }, { v: 2 }] }
    assert.equal(evaluateExpression('-items.v', data), -3)
  })
})

describe('realistic invoice scenarios', () => {
  it('computes invoice subtotal as sum of qty * unit_price', () => {
    const data = {
      line_items: [
        { quantity: 2, unit_price: 50 },
        { quantity: 1, unit_price: 25 },
      ],
    }
    assert.equal(
      evaluateExpression('sum(line_items.quantity * line_items.unit_price)', data),
      125
    )
  })

  it('computes invoice total with VAT', () => {
    const data = {
      line_items: [
        { quantity: 2, unit_price: 50 },
        { quantity: 1, unit_price: 25 },
      ],
    }
    const expr =
      'sum(line_items.quantity * line_items.unit_price) ' +
      '+ sum(line_items.quantity * line_items.unit_price) * 0.2'
    assert.equal(evaluateExpression(expr, data), 150)
  })
})
