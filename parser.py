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

def literal_identifier(s:str):
    def predicate(token:Token) -> bool:
        return token[0] == 'identifier' and token[1] == s
    return hook_str_of_function(predicate, s)

def any_special_char_in(s:str):
    def predicate(token:Token) -> bool:
        return token[0] == 'char' and token[1] == s
    return hook_str_of_function(predicate, s)

arithmetic_grammar = {
    START_SYMBOL: [["sum"]],
    "sum": [["product"], ["product", any_special_char_in("+"), "sum"]],
    "product": [["factor"], ["factor", any_special_char_in("*"), "product"]],
    "factor": [["number"], [any_special_char_in("("), "sum", any_special_char_in(")")]],
    "number": [[number]]
}

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
    "sum": [["number"], [any_special_char_in("("), "sum", any_special_char_in(")")], ["sum", any_special_char_in("+"), "sum"]],
    "number": [[number]]
}

from typing import Literal, Generator

type Token = tuple[Literal['string literal'] | Literal['identifier'] | Literal['char'], str] \
    | tuple[Literal['number'], int]

def tokenizer(document: str) -> Generator[Token]:

    current_token = ""
    current_state = None # type: ignore

    WHITESPACE = lambda c : c in ' \t\n'

    ALLOWED_SPECIAL_CHARS = lambda c : c in '()[]{}<>=+*/-.'

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
    grammar: grammartype = field(default_factory=lambda : arithmetic_grammar)
    state_sets: list[list[ParsingItem]] = field(default_factory=lambda : [])

    def item_already_exists(self, i, new_item:ParsingItem):
        return any(
            other.rule == new_item.rule and other.progress == new_item.progress and other.start == new_item.start
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
                goal = other_item.goal
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
                match self.state_sets[i][j].action_needed:
                    case 'predict' :
                        self.predict(i, j)
                    case 'scan' :
                        self.scan(i, j)
                    case 'complete' :
                        self.complete(i, j)
                j += 1

        was_parse_successful = any(
            item.start == 0 and item.is_completed for item in self.state_sets[-1]
        )

        def remove_all_incomplete_items():

            for i, state_set in enumerate(self.state_sets) :
                self.state_sets[i] = [
                    item
                    for item in state_set
                    if item.is_completed
                ]

        print([len(x) for x in self.state_sets])

        remove_all_incomplete_items()

        return was_parse_successful

@dataclass
class InvertedItem(ParsingItem):
    end: int = 0

    @staticmethod
    def from_item(item:ParsingItem, i:int):
        assert item.progress == len(item.rule)
        return InvertedItem(
            start=i,
            end=i,
            goal=item.goal,
            rule=item.rule,
            progress=len(item.rule)
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
    def invert_items(items: list[list[ParsingItem]]) -> list[list[InvertedItem]]:
        out = [[] for x in items]

        for i, state_set in enumerate(items):
            for item in state_set :
                out[item.start].append(InvertedItem.from_item(item, i))

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


root = document_to_parse_tree("3+4*5")

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
