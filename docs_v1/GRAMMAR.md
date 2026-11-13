^ = input

input = statement
     | statement ";"

statement = relation_expression
     | create_relation
     | insert_into_relation
     | "eval" scalar_expression
     | "eval" boolean_expression

create_relation = 

insert_into_relation = 

relation_expression = unary_relational_expression
     | inner_relation_expression binary_relational_operator inner_relation_expression
     | table_identifier

inner_relation_expression = unary_relational_expression
     | "(" inner_relation_expression binary_relational_operator inner_relation_expression ")"
     | table_identifier

table_identifier = identifier

unary_relational_expression = "select" "[" boolean_expression "]" "(" relation_expression ")"
     | "project" "[" identifier_list "]" "(" relation_expression ")"
     | "rename" "[" rename_list "]" "(" relation_expression ")"
     | "compute" "[" compute_list "]" "(" relation_expression ")"

binary_relational_operator = "union"
     | "intersect"
     | cartesian_product
     | "subtract"
     | "minus"
     | "divide"
     | join

cartesian_product = "cross"
     | "cross" "product"
     | "cartesian" "product"

join = natural_join
     | theta_join

natural_join = "join"
     | "outer" "join"
     | "left" "join"

theta_join = natural_join "[" boolean_expression "]"

boolean_expression = disjunct

disjunct = conjunct "or" disjunct
     | conjunct

conjunct = not "and" conjunct
     | not

not = boolean_factor
     | "not" boolean_factor

boolean_factor = "(" boolean_expression ")"
     | condition

condition = boolean_literal
     | scalar_expression "<"|">" scalar_expression
     | scalar_expression "=" scalar_expression
     | scalar_expression "<"|">" "=" scalar_expression
     | scalar_expression "=" "=" scalar_expression

boolean_literal = "true"
     | "false"

scalar_expression = numeric_expression
     | "string_literal"

numeric_expression = additive

additive = multiplicative "+" | "-" additive
     | multiplicative

multiplicative = unm "*" | "/" multiplicative
     | unm

unm = factor
     | "-" factor

factor = "(" additive ")"
     | number
     | attribute

number = number
     | number "." number
     | "." number

attribute = identifier
     | identifier "." identifier
     | "left" "." identifier
     | "right" "." identifier

identifier_list = attribute
     | attribute identifier_list
     | attribute "," identifier_list

rename_list = rename
     | rename rename_list
     | rename "," rename_list

rename = identifier "-" ">" identifier

compute_list = compute
     | compute compute_list
     | compute "," compute_list

compute = numeric_expression "as" identifier



description of ambiguity:

at one point, my grammar used something like:

additive = additive + additive
    | number

(sparing the details for this example)

I really thought this would work with my parser. It works with the recognizer! But the parser fails to parse an ambiguous grammar. 

Here are two possible parse trees for the same input to demonstrate that this grammar is ambiguous

"1 + 2 + 3"

additive
    additive
        additive
            1
        additive
            2
    additive
        3

additive
    additive
        1
    additive
        additive
            2
        additive
            3



precedence and associativity:

arithmetic operations in order of highest to lowest precedence:
parentheses, literal numbers, or an attribute
- (unary negation)
*/  
+-  

boolean operations in order of highest to lowest precedence
parentheses, true/false, or an attribute
not
and
or

all binary arithmetic and boolean operators (+ - * / and or) are right associative, though this doesn't make a difference

all other operators don't have precedence/associativity since they require you to use parentheses. e.g:

"A union B minus C" is not a valid expression, the user would have to specify either "(A union B) minus C" or "A union (B minus C)". I made this decision because I don't personally see an obvious order in these operations, so any associativity rule would confuse me. 