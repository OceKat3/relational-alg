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
        ["attribute"]
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
        ["multiplicative"]
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

type Token = tuple[Literal['string literal'] | Literal['identifier'] | Literal['char'], str] \
    | tuple[Literal['number'], int]

def tokenizer(document: str) -> Generator[Token]:

    current_token = ""
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
            yield ('string literal', current_token)
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
            yield ('identifier', current_token)
            yield from document_begin(next_char)
        yield from []

    def number(next_char) -> Generator[Token]:
        nonlocal current_state, current_token
        if NUMBER(next_char) :
            current_token += next_char
        else :
            yield ('number', int(current_token))
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
            yield ('char', next_char)
        else:
            raise SyntaxError(f'unexpected character: "{next_char}"')
        yield from []
    current_state:Callable[..., Generator[Token]] = document_begin

    def document_loop() -> Generator[Token]:
        for character in document :
            yield from current_state(character)

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
                print('no candidates', i, goal)
                return []
            
            farthest_end = max(candidates, key=lambda c : c.end).end

            return [item for item in candidates if item.end == farthest_end]
            
            # print(candidates)
            # quit()

        def diagnose_recursively(item:InvertedItem) -> set[Terminal]:

            assert item.progress < len(item.rule)

            if is_token_terminal(item.next_token) :
                assert is_token_terminal(item.next_token)
                return set([item.next_token]) #type: ignore
            else :
                next_goal = item.next_token
                assert isinstance(next_goal, str)

                items_which_would_have_completed_this_one = find_partially_completed_items(item.end, next_goal)

                out:set[Terminal] = set()
                for item in items_which_would_have_completed_this_one :
                    out.update(diagnose_recursively(item))

                return out
        
        possible_terminals = diagnose_recursively(
            find_partially_completed_items(0, START_SYMBOL)[0]
        )

        print([x.__str__() for x in possible_terminals])


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

        print([len(x) for x in self.state_sets])

        print(
            self.repr_state_sets(self.state_sets)
        )

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
            start=i,
            end=i,
            goal=item.goal,
            rule=item.rule,
            progress=item.progress
        )

class Parser:

    inverted_items: list[list[InvertedItem]]
    document: list[Token]
    seen_set:list[InvertedItem] = list()

    def __init__(self, items: list[list[ParsingItem]], document: list[Token]):
        self.inverted_items = Parser.invert_items(items)
        self.document = document

        print(Recognizer.repr_state_sets(self.inverted_items))

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

        print('    ' * recursive_depth, i, end=" ")
        item = self.get_max_length_item(i, symbol, end)
        print(str(item))
        self.seen_set.append(item)

        print(f"={i}= {item.__str__()}")

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


    def reduce(self, node:Parser.Node):

        match node.item.goal, *node.children :
            case 'statement', Parser.Node() as child:
                return self.create_node(
                    'relation',
                    self.reduce(child)
                )
            case 'unary_relational_expression', operation, _, Parser.Node() as phi, _, _, Parser.Node() as relation, _ :
                assert not isinstance(operation, Parser.Node)
                return self.create_node(
                    operation[1],
                    self.reduce(phi),
                    self.reduce(relation)
                )
            case _, Parser.Node() as child:
                return self.reduce(child)
            case _, token :
                assert not isinstance(token, Parser.Node)
                return 

from pprint import pprint

def document_to_parse_tree(document:str) -> Parser.Node:

    tokens = list(tokenizer(document))

    pprint(tokens)

    recognizer = Recognizer(document=tokens)
    recognizer.earley_recognize()

    # print(
    #     recognizer.repr_state_sets(
    #         # Parser.invert_items(
    #             recognizer.state_sets
    #         # )
    #     )
    # )

    root = Parser(document=recognizer.document, items=recognizer.state_sets).create_tree()
    return root


root = document_to_parse_tree("project [col1 col2] (people union employees")

pprint(
    root.to_printable_graph()
)



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
