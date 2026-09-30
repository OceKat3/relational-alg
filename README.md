# relational-alg

A relational algebra query parser written for COMP3005 Database Management Systems at carleton. Relational algebra is an imperative language, i.e. when you write relational algebra you are describing what computations you want the database engine to do.

This project was made with zero AI, and I streamed the whole development process on youtube. It was very fun!

The tokenizer and earley parser were written in such a way that they can be used to parse any other language.

## how to use

no dependencies other than the python standard lib!

python repl.py

if you'd like to see parse tree or AST representations, change the 'mode' variable in repl.py

## features

Relational: 

union, intersect, subtract, divide, join, cartesian product

use the identifiers 'left' and 'right' to disambiguate a self-join without renaming anything!

select[predicate], project[columns], rename[columns->columns], compute[expressions]

Compute is a unary operation I came up with to try and capture the fact that SQL lets you write calculations in your SELECT statement. For example: compute[hourly_wage * 40 as paycheck](employees)

Boolean/math:

All the regular boolean and basic math stuff. Operations like exponentiation, modulo, rounding, and bitwise operations are not implemented.

addition works as string concatenation!


## limitations

- no right joins, just left joins
- no deduplication mechanism
- not thoroughly tested
- extremely poor performance, because I just wanted to write very readable code. In python readable code tends to use lots of dynamic memory (sets, dataclasses)