CPython, intel xeon processor

1. does the size of relations affect the complexity of join?

20   400 comparisons   34 output tuples   wall:  0.003309011459350586   
40   1600 comparisons   76 output tuples   wall:  0.013733148574829102   
80   6400 comparisons   156 output tuples   wall:  0.04928851127624512   
160   25600 comparisons   314 output tuples   wall:  0.19138813018798828   
320   102400 comparisons   638 output tuples   wall:  0.7772610187530518   
640   409600 comparisons   1272 output tuples   wall:  3.12143611907959   
1280   1638400 comparisons   2560 output tuples   wall:  12.418636798858643

I had to significantly scale down this experiment because my query execution performs so poorly. The ask in the assignment was for up to 64k tuples. 

The number of output tuples scales with n (with a bit of randomness)
The number of comparisons is exactly n^2 due to the nested loop
Wall time scales with comparisons, roughly quadrupling every time n doubles.

2. Plot time against n on log log axes

Did this on desmos, see desmos_logplot_quadratic.png

What's cool about loglog plots is that straight lines represent power-law relationships. 

That is, if:
log(y) = mlog(x)+b, then
y = x^m * e^b

So when we see a slope of 2, we know that means the independent variable x (in this case time) is being squared. That makes sense.

3. does the size of relations affect the complexity of operations like select/project?

1000   1000 comparisons   956 output tuples   wall:  0.0049828290939331055   
2000   2000 comparisons   1951 output tuples   wall:  0.007646441459655762   
4000   4000 comparisons   3963 output tuples   wall:  0.014328300952911377   
8000   8000 comparisons   7962 output tuples   wall:  0.02825102210044861   
16000   16000 comparisons   15947 output tuples   wall:  0.05746003985404968   
32000   32000 comparisons   31954 output tuples   wall:  0.11221146583557129   
64000   64000 comparisons   63960 output tuples   wall:  0.22327980399131775 

desmos_logplot_linear.png

Select performs so much better than join that i can run 64000 tuples like the assignment asks. I think this is clearly because select touches each row only once. Select does not involve nested for loops.

The logplot is noisier but the relationship is roughly linear. The relationship to comparisons is exactly linear

4. 

Using desmos, I visually estimated a line of best fit: 

time = n^2 / 130000 seconds

with n equal to one million, the join would take (according to this formula) over 7 million seconds. No good!

5. does the match rate affects the number of comparisons a join makes? wall time?

match rate 0.1714     40000 comparisons   32 output tuples   wall:  0.3132956027984619   
match rate 0.3086     40000 comparisons   59 output tuples   wall:  0.31346577405929565   
match rate 0.5555     40000 comparisons   104 output tuples   wall:  0.30502814054489136   
match rate 1.0        40000 comparisons   200 output tuples   wall:  0.30263417959213257   
match rate 1.8        40000 comparisons   355 output tuples   wall:  0.306282639503479   
match rate 3.24       40000 comparisons   636 output tuples   wall:  0.31571733951568604   
match rate 5.8320     40000 comparisons   1162 output tuples   wall:  0.30410295724868774   
match rate 10.497     40000 comparisons   2029 output tuples   wall:  0.30684012174606323   
match rate 18.895     40000 comparisons   3624 output tuples   wall:  0.3060912489891052   
match rate 34.012     40000 comparisons   6680 output tuples   wall:  0.3067479133605957   
match rate 61.222     40000 comparisons   9825 output tuples   wall:  0.3049757480621338 

There is practically zero correlation between match rate and execution time, and there is truly zero correlation with the number of comparisons.

It makes sense that, with my naive join algorithm, i will check every element of the cartesian product, regardless of however sparse the join might actually be. So the number of comparisons will always be n^2

I would have expected any relationship from match rate to wall clock time at all. I'm a little surprised, but I imagine it's because most execution time gets eaten by comparison and not by writing output rows.

6. How to make the system faster, so that a million tuples would be possible?

The most obvious problem with my join algorithm is that it checks all n^2 pairs from the joinees. If you're given an arbitrary predicate, then you probably have to check all pairs. But typically we aren't actually given arbitrary predicates, we get equi-joins. My guess is that B-trees or hash-style datastructures can significantly speed up equi-join operations, so long as at least one of the joining columns is indexed. When you have one tuple of an equi-join, you know exactly what to look for in the corresponding tuples, because the corresponding attribute must be equal! The difference between O(n^2) and O(n log n) is huge, so I think the datastructures are worth it. 