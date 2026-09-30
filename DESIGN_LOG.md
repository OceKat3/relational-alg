I only started writing this design log in my last session, so I didn't have a chance to log what I was doing as I was doing it. Luckily, there is a github commit history, and I streamed my entire development process on youtube.

Here are all of my streams in order. Don't mind my taste in music

https://youtube.com/live/3MGGSpA5Ch4
https://youtube.com/live/WGyaibrv1e8
https://youtube.com/live/2Aihipaw874
https://youtube.com/live/dj2PB00w1uI
https://youtube.com/live/LTlXlkWcnGg
https://youtube.com/live/XSSKemw3FOI
https://youtube.com/live/DxOTx-qbn3c
https://youtube.com/live/7kun8c49514 (i am writing the design log in this stream, hello hi hello :3 )

^ at like 2:08:00 you can see the moment i discovered a very stupid bug

I originally wanted to write this project in the functional language idris2, because I thought a dependent type system would help. It was very stupid to think i could learn a functional programming language AND dependent type theory AND write a parser in two weeks. So instead i'm using my most comfortable language, python.

It was also clear from the beginning that this project would use zero AI. It's an extra challenge I imposed on myself, and I'm very glad I did. This project has been possibly the most fun I've ever had this year in computer science, thank you Prof. Orogat!!

I started with researching parsing methods. I wrote a throwaway recursive descent parser, and then learned about Earley recognizing/parsing. I decided to use Earley parsing becasue the algorithm makes more sense to me, and it can parse left-recursion or right-recursion. (just not both in the same rule, because that's ambiguity! my parser cannot handle ambiguous grammars, though the recognizer can)

Unlike with recursive descent, the Earley algorithm distinguishes between recognizing and parsing. Recognizing just determines whether or not a string matches the grammar, and then parsing creates a parse tree. Luckily, an Earley recognizer produces exactly the data structure we need to produce a parse tree, the Earley state sets. I implemented the recognizer and parser as separate classes (with those exact names)

My Earley recognizer first operated on raw strings, but then I wrote a tokenizer since i realized it would make my life way easier. It was not hard to convert the parser from using strings as terminals to using tokens as terminals because python strings use a very similar syntax to python arrays, and I had decided on the abstraction that all terminals are representated as functions which return True when they see their terminal. 

The tokenizer creates three kinds of tokens: identifiers, special characters, and numbers. Each token also has a string or int to tell you what it actually is, and each token stores where it exists in the user's input string. I represent tokens as tuples, e.g. ('identifier', 'union', 20). 

Decimal numbers e,g, 3.14 are represented as three tokens: the number '3', the special character '.', and the number '14'. Later, we can turn these into a decimal number.

At this point, I had a tokenizer followed by a recognizer. After much debugging, I finally also had a parser. The big 'trick' for parsing earley grammars comes from Loup Vaillant's blog: you invert the Earley state sets so that an Earley item's start and end index take on opposite roles. Loup does a better job of explaining it: https://loup-vaillant.fr/tutorials/earley-parsing/parser#:~:text=Searching%20from%20the%20wrong%20end

For a while, my grammar was ambiguous which caused me some serious pain. My parser fails whenever the grammar is ambiguous, but I didn't realize this, nor did I realize that my grammer was ambiguous. An example ambiguous rule:

sum = sum + sum
sum = number

With this rule, there are multiple interpretations of 1+2+3, i.e. all the ways you can associate them, either (1+2)+3 or 1+(2+3). Addition is associative so this doesn't affect the output, but my parser has to work so I just chose one. My fixed rule looks like:

sum = number + sum
i.e. it is right-associative.

( the actual rule is additive = multiplicative ("+"|"-") additive. I had a lot of fun with the words, like additive, multiplicative, and conjunct/disjunct which i think are the right words for boolean AND/OR expressions )

Around this time, after fixing the ambiguity, I also came up with my algorithm for displaying helpful errors in the recognizer. I'm very proud of it! see Recognizer.diagnose_problem. Here's one of the only comments in the entire project, which I wrote to help me figure out the algorithm:

"""
1. invert the state sets, complete and incomplete
2. find the maximum k for which there is a ((0) ^ -> alpha (end=k)) (there may be multiple items)
3. since the parse failed, that item(s) still has a next_token. it is not complete
4. recurse through next_token until they are all terminals. Then output, "expected one of (terminal1, terminal2) at k" 
"""

I wasn't happy with just making a parse tree; I wanted to turn the parse tree into an abstract syntax tree. For one, the parse tree has tons of redundant nodes. I'd also like to try continuing with this project to make a DBMS, so I think making a good AST now will save me some pain in the future. 

The conversion from parse tree to AST happens in RelationalTreeReducer.reduce, which is just a huge recursive pattern-matcher. Python tuples and dataclasses came in to save my life here, because they work so well with python's pattern matcher. If there are any bugs in my code, i suspect they're here because it's mostly untyped, and every rule from the grammar needs to get caught by this match statement.


- I got really frustrated with trying to do python imports across directories (test files in /test need to import parser) so I just created a test.py file in the same directory. The solution involves making a pyproject.toml which is too much work

- Battled a nasty error in the grammar again. I was doing "not" and unary negation incorrectly. I incorporated subtraction into the "multiplicative" nonterminal, when really subtraction deserves to be its own nonterminal

- Made the decision that relations will all be nameless, and some attribute names will have dots in them. Calling attributes by name is flexible, so you don't always have to specify a relation name. Relations being nameless means there is no need to choose a name after e.g. unioning or joining

