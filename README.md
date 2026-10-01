# relational-alg

A relational algebra query parser written for COMP3005 Database Management Systems at Carleton. Relational Algebra is a languaage, i.e. when you write relational algebra you are describing what computations you want the database engine to do. This project is my own interpretation of a relational algebra language, with a couple features I thought would be cool.

This project was made with zero AI, and I streamed the whole development process on youtube. It was very fun!

## how to use

no dependencies other than the python standard lib!

the main user interface is the repl:
python repl.py

"eval" lets you run scalar expressions:
query > eval 1 + 2 * 3

"mode" changes the REPL mode. "query" is the default which tries to evaluate your input and produce a relation or scalar. "ast" prints the python objects representing the expression, and "parsetree" shows the result after recognizing and parsing (i.e. also before generating an ast) 
mode query
mode ast
mode parsetree

any statement that doesn't start with eval or mode is treated as a relational query. A few relations in example_relations.py get loaded into the REPL. e.g:

query > employees

query > employees join[ left.managerid = right.id ] employees

query > project [ departments.name ] (employees join[departmentid = departments.id] departments)


## language features

Relational: 

union, intersect, subtract, divide, join, cartesian product

use the identifiers 'left' and 'right' to disambiguate a self-join without renaming anything!

select[predicate], project[columns], rename[columns->columns], compute[expressions]

Compute is a unary operation I came up with to try and capture SQL's ability to express calculations in a SELECT statement. For example: compute[hourly_wage * 40 as paycheck](employees)

Boolean/math:

All the regular boolean and basic math stuff. Operations like exponentiation, modulo, rounding, and bitwise operations are not implemented.

addition also works as string concatenation!

## earley parsing

I'm using a bit of an unconventional parsing algorithm, compared to the usual recursive descent (and variations). I learned about Earley Parsers from some reddit or stackoverflow post, and it sent me down a huge rabbit hole. Wikipedia has a surprisingly good description of the Earley recognizer algorithm, and Loup Vaillant talks about creating parse trees too. I have a few reasons to use an earley parser:

- The algorithm just makes more sense to me!
- Earley state sets make it possible to implement pretty good syntax error handling, by providing suggestions to the user. e.g:

 query > select[true](employees
(SyntaxError) did you mean:
'join', or 'left', or 'outer', or 'cartesian', or 'cross', or 'intersect', or 'union', or 'divide', or 'minus', or 'subtract', or ')' 
at 'select[true](employees' ?

- The Earley parsing algorithm splits parsing into two steps, recognizing and parsing. Recognizing determines whether or not the document follows the grammar, and produces the necessary data structure (Earley items) for a parser to make an actual parse tree. I think more weakly coupled components is a good thing!
- The Earley recognizer works for any context free grammar, even an ambiguous one! Both the recognizer and parser were written generically so e.g. I could use the same code to parse SQL later in the dbms part of this assignment, if I choose to continue. In general, an Earley recognizer+parser places fewer restrictions on the grammar than other parsers like a predictive recursive descent parser. 

The most obvious downside of the Earley algorithm is that it can be very expensive: O(n^3) time and O(n^2) space, where n is the length of the input. I think this is an acceptable cost, and I've never had any performance problems with my small queries. This is something to keep in mind if this system should ever parse larger queries

The Earley algorithm, as I implemented it, can't handle any rules which parse the empty string. In 2002 a fix was published to the Earley empty string bug, but I have not implemented that fix! So I have strategically avoided any nullable/empty rules in my grammar. The fix is not terribly complicated, but it would hurt code readability.

https://loup-vaillant.fr/tutorials/earley-parsing/
https://en.wikipedia.org/wiki/Earley_parser

Jay Earley's paper is hard to read but goes very deep:
https://web.archive.org/web/20170922004954/http://reports-archive.adm.cs.cmu.edu/anon/anon/usr/ftp/scan/CMU-CS-68-earley.pdf

## limitations

- no right joins, just left joins
- no deduplication mechanism
- extremely poor performance on large relations, especially on joins
- no aggregation or groupby
- no sorting
- no subqueries