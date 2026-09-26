from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable

type Terminal = Callable[[Token], bool]
type grammartype = dict[str, list[list[str | Terminal]]]


START_SYMBOL = "^"

from functools import wraps

def hook_str_of_function(func:Terminal, display_text:str):
    setattr(func, "__str__", lambda : display_text)
    return func

def string_literal(token:Token) -> bool:
    return token[0] == 'string literal'
hook_str_of_function(string_literal, 'string_literal')

def number(token:Token) -> bool:
    return token[0] == 'number'
hook_str_of_function(number, 'number')

protected_identifiers = set()

def literal_identifier(s:str):
    global protected_identifiers
    protected_identifiers.add(s)

    def predicate(token:Token) -> bool:
        return token[0] == 'identifier' and token[1] == s
    return hook_str_of_function(predicate, s)

def identifier(token:Token):
    return token[0] == 'identifier' and token[1] not in protected_identifiers
hook_str_of_function(identifier, 'identifier')

def special_char(s:str):
    def predicate(token:Token) -> bool:
        return token[0] == 'char' and token[1] == s
    return hook_str_of_function(predicate, s)

literal = special_char

arithmetic_grammar = {
    START_SYMBOL: [["sum"]],
    "sum": [["product"], ["sum", special_char("+"), "sum"]],
    "product": [["factor"], ["product", special_char("*"), "product"]],
    "factor": [[number], [special_char("("), "sum", special_char(")")]],
}

relational_algebra_grammar = {
    START_SYMBOL: [["input"]],
    "input": [["statement"], ["statement", special_char(";")], ["statement", special_char(';'), "input"]],
    "statement": [
        ["relation_expression"],  # dql
        ["create_relation"],      # ddl
        ["insert_into_relation"], # dml
    ],

    "create_relation":[],
    "insert_into_relation":[],

    "relation_expression": [
        ["unary_relational_expression"],
        ["inner_relation_expression", "binary_relational_operator", "inner_relation_expression"],
        [identifier]
    ],

    "inner_relation_expression": [
        ["unary_relational_expression"],
        [special_char('('), "inner_relation_expression", "binary_relational_operator", "inner_relation_expression", special_char(')')],
        [identifier]
    ],

    "unary_relational_expression": [
        [literal_identifier("select"), special_char('['), "condition", special_char(']'), special_char('('), "relation_expression", special_char(')')], 
        [literal_identifier("project"), special_char('['), "identifier_list", special_char(']'), special_char('('), "relation_expression", special_char(')')], 
        [literal_identifier("rename"), special_char('['), "rename_list", special_char(']'), special_char('('), "relation_expression", special_char(')')]
    ],
    "binary_relational_operator": [
        [literal_identifier("union")], 
        [literal_identifier("intersect")], 
        ["cartesian_product"],
        [literal_identifier("subtract")],
        [literal_identifier("divide")],
        
    ],
    "cartesian_product": [
        [literal_identifier("cross")], 
        [literal_identifier("cross"), literal_identifier("product")], 
        [literal_identifier("cartesian"), literal_identifier("product")]
    ],

    "boolean_expression": [
        ["disjunct"]
    ],
    "disjunct":[
        ["conjunct", special_char('or'), "disjunct"],
        ["conjunct"]
    ],
    "conjunct":[
        ["boolean_factor", special_char('and'), "conjunct"],
        ["boolean_factor"]
    ],
    "boolean_factor": [
        [special_char('('), "boolean_expression", special_char(')')],
        [special_char('not'), "boolean_expression"],
        ["condition"],
    ],

    "condition":[
        ["scalar"],
        ["scalar", special_char('<>'), "scalar"],
        ["scalar", special_char('='), "scalar"],
        ["scalar", special_char('<>'), special_char('='), "scalar"],
        ["scalar", special_char('='), special_char('='), "scalar"],
    ],

    "scalar":[
        ["numeric_expression"],
        ["attribute"],
    ],

    "boolean_literal": [
        [literal("true")],
        [literal("false")],
        ["attribute"]
    ],

    "numeric_expression": [
        ["additive"]
    ],

    "additive": [
        ["multiplicative", special_char('+-'), "additive"],
        ["multiplicative"],
        [special_char('-'), "multiplicative"],
    ],
    "multiplicative": [
        ["factor", special_char('*/'), "multiplicative"],
        ["factor"]
    ],
    "factor": [
        [special_char('('), "numeric_expression", special_char(')')],
        [number],
        ["attribute"],
    ],

    "attribute": [
        [identifier],
        [identifier, special_char('.'), identifier]
    ],

    "identifier_list": [
        [identifier],
        [identifier, "identifier_list"],
        [identifier, special_char(','), "identifier_list"]
    ],

    "rename_list": [
        ["rename"],
        ["rename", "rename_list"],
        ["rename", special_char(','), "rename_list"]
    ],
    "rename": [
        [identifier, special_char('-'), special_char('>'), identifier]
    ]
    
}

from typing import Any
class AlgebraNode:
    def eval(self, *a, **kwa) -> Any:
        raise NotImplemented


class ScalarExpression(AlgebraNode):
    def eval(self, bound_identifiers:dict[str, Any]) -> int | float | str:
        raise NotImplemented

class BooleanExpression(AlgebraNode):
    def eval(self, bound_identifiers:dict[str, Any]) -> bool:
        raise NotImplemented

class RelationExpression(AlgebraNode):
    def eval(self) -> list:
        raise NotImplemented

@dataclass
class UnaryRelational(AlgebraNode):
    relation: RelationExpression

@dataclass
class Project(UnaryRelational):
    columns: list[str]

@dataclass
class Select(UnaryRelational):
    predicate: BooleanExpression

@dataclass
class Rename(UnaryRelational):
    renames: dict[str, str]

from typing import Callable

@dataclass
class BinaryScalarExpression(ScalarExpression):
    left:ScalarExpression
    right:ScalarExpression

    operation: Callable

    def eval(self, *a, **kwa) -> int | float | str:
        # TODO type safety
        return self.operation(
            self.left.eval(*a, **kwa),
            self.right.eval(*a, **kwa)
        )

class Add(BinaryScalarExpression):
    operation = lambda x, y : x+y
class Subtract(BinaryScalarExpression):
    operation = lambda x, y : x-y
class Multiply(BinaryScalarExpression):
    operation = lambda x, y : x*y
class Divide(BinaryScalarExpression):
    operation = lambda x, y : x/y

class Unm(ScalarExpression):
    arg:ScalarExpression
    def eval(self, *a, **kwa) -> int | float | str:
        # TODO type safety
        return -self.arg.eval(*a, **kwa)


def check_grammar(grammar:grammartype):

    for key in grammar:
        for rule in grammar[key]:
            for symbol in rule:
                if type(symbol) == str :
                    assert symbol in grammar, f"{key} -> ...{symbol}...,   {symbol} not found in grammar"
check_grammar(relational_algebra_grammar)

"""
[('number', 3), ('char', '+'), ('number', 4), ('char', '*'), ('number', 5)]

sum
sum + product
number + product
number + product * factor
number + number * number

"""

simple_arithmetic_grammar = {
    START_SYMBOL: [["sum"]],
    "sum": [["number"], [special_char("("), "sum", special_char(")")], ["sum", special_char("+"), "sum"]],
    "number": [[number]]
}

from typing import Literal, Generator

type Token = tuple[Literal['string literal'] | Literal['identifier'] | Literal['char'], str, int] \
    | tuple[Literal['number'], int, int]

def tokenizer(document: str) -> Generator[Token]:

    current_token = ""
    document_index = 0
    current_state = None # type: ignore

    WHITESPACE = lambda c : c in ' \t\n'

    ALLOWED_SPECIAL_CHARS = lambda c : c in '()[]{}<>=+*/-.,;'

    IDENTIFIER_BEGIN = lambda c : "a" <= c <= "z" or "A" <= c <= "Z" or c == '_'
    NUMBER = lambda c : "0" <= c <= "9"
    IDENTIFIER_BODY = lambda c : IDENTIFIER_BEGIN(c) or NUMBER(c)

    STRING_BEGIN = lambda c : c == "\""
    STRING_END = lambda c : c == "\""
    STRING_ESCAPE = lambda c : c == "\\"

    def escaped_string(next_char) -> Generator[Token]:
        nonlocal current_state, current_token
        current_token += next_char
        current_state = string
        yield from []

    def string(next_char) -> Generator[Token]:
        nonlocal current_state, current_token

        if STRING_END(next_char) :
            yield ('string literal', current_token, document_index)
        elif STRING_ESCAPE(next_char) :
            current_state = escaped_string
        else :
            current_token += next_char
            current_state = string

    def identifier(next_char) -> Generator[Token]:
        nonlocal current_state, current_token

        if IDENTIFIER_BODY(next_char):
            current_token += next_char
        else:
            current_state = document_begin
            yield ('identifier', current_token, document_index-1)
            yield from document_begin(next_char)
        yield from []

    def number(next_char) -> Generator[Token]:
        nonlocal current_state, current_token
        if NUMBER(next_char) :
            current_token += next_char
        else :
            yield ('number', int(current_token), document_index)
            current_state = document_begin
            yield from document_begin(next_char)
        yield from []

    def document_begin(next_char: str) -> Generator[Token]:
        nonlocal current_state

        if IDENTIFIER_BEGIN(next_char) :
            current_state = identifier
            yield from identifier(next_char)
        elif STRING_BEGIN(next_char):
            current_state = string
        elif NUMBER(next_char) :
            current_state = number
            yield from number(next_char)
        elif WHITESPACE(next_char):
            pass
        elif ALLOWED_SPECIAL_CHARS(next_char):
            yield ('char', next_char, document_index)
        else:
            raise SyntaxError(f'unexpected character: "{next_char}"')
        yield from []
    current_state:Callable[..., Generator[Token]] = document_begin

    def document_loop() -> Generator[Token]:
        nonlocal document_index
        for character in document :
            yield from current_state(character)
            document_index += 1

        if len(current_token) > 0 :
            if current_state in [identifier, number] :
                yield from current_state(' ')
            elif current_state in [string, escaped_string] :
                raise SyntaxError('expected string to terminate at end of input')
            

    for token in document_loop():
        yield token
        current_token = ""


def is_token_terminal(token: str | Terminal | None):
    return type(token) != str

@dataclass
class ParsingItem:
    start:int
    rule: list[str | Terminal]
    goal: str
    progress:int = 0

    @property
    def next_token(self):
        return self.rule[self.progress] if self.progress < len(self.rule) else None

    @property
    def is_completed(self) -> bool:
        return self.progress == len(self.rule)

    @property
    def action_needed(self):
        if self.is_completed : return 'complete'
        
        waiting_on_terminal = is_token_terminal(self.next_token)

        return 'scan' if waiting_on_terminal else 'predict'

    @staticmethod
    def token_to_str(token: str | Terminal):
        return token.__str__()

    def __str__(self) -> str:
        return f"{self.goal} -> {' '.join(map(self.token_to_str, self.rule[:self.progress]))} . {' '.join(map(self.token_to_str, self.rule[self.progress:]))}  ({self.start})"

@dataclass
class Recognizer:

    document: list[Token]
    real_string_input: str
    grammar: grammartype = field(default_factory=lambda : relational_algebra_grammar)
    state_sets: list[list[ParsingItem]] = field(default_factory=lambda : [])

    def item_already_exists(self, i, new_item:ParsingItem):
        return any(
            other.rule == new_item.rule and other.progress == new_item.progress and other.start == new_item.start and other.goal == new_item.goal
            for other in self.state_sets[i]
        )

    @staticmethod
    def repr_state_sets(state_sets) -> str :
        return "\n".join(
            f"=== {i} ===\n{'\n'.join(map(str, state_set))}"
            for i, state_set in enumerate(state_sets)
        )

    def complete(self, i, j):

        item:ParsingItem = self.state_sets[i][j]
        assert item.is_completed

        for other_item in self.state_sets[item.start] :

            if other_item.next_token != item.goal : continue

            next_item = ParsingItem(
                start = other_item.start,
                progress = other_item.progress + 1,
                rule = other_item.rule,
                goal = other_item.goal,
            )

            if self.item_already_exists(i, next_item) : continue

            self.state_sets[i].append(next_item)

    def predict(self, i, j):

        item:ParsingItem = self.state_sets[i][j]
        next_token = item.next_token
        assert isinstance(next_token, str)

        child_rules = self.grammar[next_token]

        for child_rule in child_rules :

            new_item = ParsingItem(rule=child_rule, goal=next_token, start=i)
            if self.item_already_exists(i, new_item) : continue

            self.state_sets[i].append(new_item)

    def scan(self, i, j):
        item:ParsingItem = self.state_sets[i][j]
        terminal_predicate = item.next_token
        assert isinstance(terminal_predicate, Callable)

        if i + 1 >= len(self.state_sets) or i >= len(self.document) : return

        next_symbol_in_stream = self.document[i]

        if terminal_predicate(next_symbol_in_stream) :
            next_item = ParsingItem(
                start = item.start,
                progress = item.progress + 1,
                rule = item.rule,
                goal = item.goal
            )

            if self.item_already_exists(i+1, next_item) : return
            self.state_sets[i+1].append(next_item)

    def diagnose_problem(self):

        if len(self.document) == 0 : 
            raise SyntaxError('recognizer got empty document, or no tokens were read')

        """
        1. invert the state sets, complete and incomplete
        2. find the maximum k for which there is a ((0) ^ -> alpha (end=k)) (there may be multiple items)
        3. since the parse failed, that item(s) still has a next_token. it is not complete
        4. recurse through next_token until they are all terminals. Then output, "expected one of (terminal1, terminal2) at k" 
        """

        inverted_state_sets = Parser.invert_items(self.state_sets, unsafe=True)

        def find_partially_completed_items(i:int, goal:str) -> list[InvertedItem]:

            candidates = [item for item in inverted_state_sets[i] if item.goal == goal]

            candidates = sorted(candidates, key=lambda item : item.end, reverse=False)
            
            if len(candidates) == 0 :
                # print('no candidates', i, goal)
                return []
            
            farthest_end = max(candidates, key=lambda c : c.end).end
            # print(goal, farthest_end)
            return [item for item in candidates if item.end >= farthest_end/2]
            
            # print(candidates)
            # quit()

        def diagnose_recursively(item:InvertedItem) -> set[InvertedItem]:

            # assert item.progress < len(item.rule)
            if item.progress == len(item.rule) : return set()

            if is_token_terminal(item.next_token) :
                assert is_token_terminal(item.next_token)
                return set([item]) #type: ignore
            else :
                next_goal = item.next_token
                assert isinstance(next_goal, str)

                items_which_would_have_completed_this_one = find_partially_completed_items(item.end, next_goal)

                out:set[InvertedItem] = set()
                for item in items_which_would_have_completed_this_one :
                    out.update(diagnose_recursively(item))

                return out
        
        items_waiting_for_terminal = diagnose_recursively(
            find_partially_completed_items(0, START_SYMBOL)[0]
        )

        farthest_parse_distance = max(items_waiting_for_terminal, key=lambda c : c.end).end
        farthest_parsed_items = [x for x in items_waiting_for_terminal if x.end == farthest_parse_distance and x.end > 0]

        def get_error_message(problem_items: list[InvertedItem]) -> str:

            problem_items = sorted(problem_items,key=lambda item : len(item.goal))

            previous_token_document_pos = self.document[problem_items[0].end - 1][2]

            preview_slice = slice(max(0,previous_token_document_pos-40), min(previous_token_document_pos+5, len(self.real_string_input)))

            document_neighbourhood = self.real_string_input[preview_slice]
            marker = ''.join([('^' if i == previous_token_document_pos else ' ') for i in range(len(self.real_string_input))][preview_slice])

            def terminal_to_str(item:InvertedItem):
                t:Terminal = item.next_token #type: ignore
                if t == identifier : return 'an identifier'
                if t == number : return 'a number'
                return f"'{t.__str__()}'"

            recommendations = []
            for item in problem_items :
                recommendation = terminal_to_str(item)
                if recommendation not in recommendations :
                    recommendations.append(recommendation)

            return f"did you mean:\n{', or '.join(recommendations)} \nat '{document_neighbourhood}' ?" \
                 f"\n     {marker}"
        

        raise SyntaxError(get_error_message(farthest_parsed_items))

    def earley_recognize(self):

        self.state_sets = [
            [] for x in self.document
        ] + [[]]

        self.state_sets[0] = [
            ParsingItem(rule=x, start=0, goal=START_SYMBOL)
            for x in self.grammar[START_SYMBOL]
        ]

        for i in range(len(self.document) + 1) :
            j = 0
            while j < len(self.state_sets[i]):

                if 'input -> statement .  ;  (0)' in self.state_sets[i][j].__str__() :
                    print(i, "!!!!!!!!!!! ", self.state_sets[i][j].action_needed)

                match self.state_sets[i][j].action_needed:
                    case 'predict' :
                        self.predict(i, j)
                    case 'scan' :
                        self.scan(i, j)
                    case 'complete' :
                        self.complete(i, j)
                j += 1

        was_parse_successful = any(
            item.start == 0 and item.is_completed and item.goal==START_SYMBOL for item in self.state_sets[-1]
        )

        if not was_parse_successful :
            self.diagnose_problem()
            quit()

        def remove_all_incomplete_items():

            for i, state_set in enumerate(self.state_sets) :
                self.state_sets[i] = [
                    item
                    for item in state_set
                    if item.is_completed
                ]

        # print([len(x) for x in self.state_sets])

        # print(
        #     self.repr_state_sets(self.state_sets)
        # )

        remove_all_incomplete_items()

        return was_parse_successful

@dataclass
class InvertedItem(ParsingItem):
    end: int = 0

    @staticmethod
    def from_item(item:ParsingItem, i:int, unsafe=False):
        if not unsafe:
            assert item.progress == len(item.rule)
        return InvertedItem(
            start=item.start,
            end=i,
            goal=item.goal,
            rule=item.rule,
            progress=item.progress
        )

    def __hash__(self) -> int:
        return str(self).__hash__()

    def __str__(self) -> str:
        return f"{self.start} {self.goal} -> {' '.join(map(self.token_to_str, self.rule[:self.progress]))} . {' '.join(map(self.token_to_str, self.rule[self.progress:]))}  ({self.end})"
    

class Parser:

    inverted_items: list[list[InvertedItem]]
    document: list[Token]
    seen_set:list[InvertedItem] = list()

    def __init__(self, items: list[list[ParsingItem]], document: list[Token]):
        self.inverted_items = Parser.invert_items(items)
        self.document = document

        # print(Recognizer.repr_state_sets(self.inverted_items))

    @dataclass
    class Node:
        children: list[Parser.Node | Token]
        item:InvertedItem

        @property
        def symbol(self) -> str:
            return self.item.goal

        def to_printable_graph(self):
            return (self.symbol, [
                child if isinstance(child, tuple) else child.to_printable_graph() for child in self.children
            ])

        

    @staticmethod
    def invert_items(items: list[list[ParsingItem]], unsafe=False) -> list[list[InvertedItem]]:
        out = [[] for x in items]

        for i, state_set in enumerate(items):
            for item in state_set :
                out[item.start].append(InvertedItem.from_item(item, i, unsafe))

        return out

    def get_max_length_item(self, i:int, symbol:str, end:int) -> InvertedItem:
        
        state_set = self.inverted_items[i]
        
        return max(
            [item for item in state_set if item.goal == symbol and item not in self.seen_set and item.end <= end],
            key = lambda item : item.end,
        )

    def create_tree(self, i=0, symbol=START_SYMBOL, end=-1, recursive_depth:int = 0) -> Node :
        if end == -1 : end = len(self.document)

        print('    ' * recursive_depth, end=" ")
        item = self.get_max_length_item(i, symbol, end)
        print(str(item))
        self.seen_set.append(item)

        # print(f"={i}= {item.__str__()}")

        if symbol == START_SYMBOL and item.end != len(self.document) :
            raise SyntaxError(f'Failed to fully parse input')

        children:list[Parser.Node | Token] = []

        document_position = i
        
        for child_symbol in item.rule :

            if is_token_terminal(child_symbol) :
                children.append(self.document[document_position])
                document_position += 1
            else:
                assert isinstance(child_symbol, str)

                child_node = self.create_tree(document_position, child_symbol, end=item.end, recursive_depth=recursive_depth+1)
                children.append(child_node)
                document_position = child_node.item.end

        return Parser.Node(
            item=item,
            children=children
        )


@dataclass    
class RelationalTreeReducer:

    def create_node(self, kind, *children):
        return (kind, children)

    def reduce(self, node:Parser.Node) -> Any:

        match node.item.goal, *node.children :
            
            case 'unary_relational_expression', ('identifier', 'select', _), _, Parser.Node() as phi, _, _, Parser.Node() as relation, _ :
                return Select(
                    self.reduce(relation),
                    self.reduce(phi)
                )
            case 'unary_relational_expression', ('identifier', 'project', _), _, Parser.Node() as column_list, _, _, Parser.Node() as relation, _ :
                return Project(
                    self.reduce(relation),
                    self.reduce(column_list)
                )
            case 'unary_relational_expression', ('identifier', 'rename', _), _, Parser.Node() as renames, _, _, Parser.Node() as relation, _ :
                return Rename(
                    self.reduce(relation),
                    self.reduce(renames)
                )

            case 'identifier_list', ('identifier', id, _) :
                return [id]

            case 'identifier_list', ('identifier', id, _), Parser.Node() as rest_of_list :
                return [id] + self.reduce(rest_of_list)
            case 'identifier_list', ('identifier', id, _), _, Parser.Node() as rest_of_list :
                return [id] + self.reduce(rest_of_list)
            
            
            case _, Parser.Node() as child:
                return self.reduce(child)
            
            case _, token :
                assert not isinstance(token, Parser.Node)
             

from pprint import pprint

def document_to_parse_tree(document:str) -> Parser.Node:

    tokens = list(tokenizer(document))

    # pprint(tokens)

    recognizer = Recognizer(document=tokens, real_string_input=document)
    recognizer.earley_recognize()

    # print(
    #     recognizer.repr_state_sets(
    #         # Parser.invert_items(
    #             recognizer.state_sets
    #         # )
    #     )
    # )

    root = Parser(document=recognizer.document, items=recognizer.state_sets).create_tree()

    actualroot = RelationalTreeReducer().reduce(root)

    return actualroot



root = document_to_parse_tree("project [col1 col2] (mytable)")

print()
pprint(root)

# pprint(
#     root.to_printable_graph()
# )


# assert list(tokenizer(""" 
# pprint(
#     root.to_printable_graph()
# )
# """)) == [
#     ('identifier', 'pprint'),
#     ('char', '('),
#     ('identifier', 'root'),
#     ('char', '.'),
#     ('identifier', 'to_printable_graph'),
#     ('char', '('),
#     ('char', ')'),
#     ('char', ')')
# ]
