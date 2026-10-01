# relational-alg

A relational algebra query parser written for COMP3005 Database Management Systems at Carleton. Relational Algebra is a languaage, i.e. when you write relational algebra you are describing what computations you want the database engine to do. This project is my own interpretation of a relational algebra language, with a couple features I thought would be cool.

This project was made with zero AI, and I streamed the whole development process on youtube. It was very fun!

## how to use

no dependencies other than the python standard lib!

the main user interface is the repl:
python repl.py

"eval" lets you run scalar expressions:
eval 1 + 2 * 3

"mode" changes the REPL mode. "query" is the default which tries to evaluate your input and produce a relation or scalar. "ast" prints the python objects representing the expression, and "parsetree" shows the result after recognizing and parsing (i.e. also before generating an ast) 
mode query
mode ast
mode parsetree

any statement that doesn't start with eval or mode is treated as a relational query. The project comes with some default relations in example_relations.py, which are loaded into the REPL. e.g:

query > employees

query > employees join[ left.managerid = right.id ] employees

query > project [ departments.name ] (employees join[departmentid = departments.id] departments)




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
- no aggregation or groupby
- no sorting