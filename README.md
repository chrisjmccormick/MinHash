MinHash
=======

This project demonstrates using the MinHash algorithm to search a large 
collection of documents to identify pairs of documents which have a lot of
text in common.

This code goes along with a tutorial on MinHash on my blog, here:
https://chrisjmccormick.wordpress.com/2015/06/12/minhash-tutorial-with-python-code/

The code includes a sample dataset of 10,000 articles containing 80 examples of
plagiarism. That is, there are 80 articles in the dataset which are identical
or nearly identical to another article in the dataset. 

I've also included smaller subsets of the data that you can experiment with, 
since the full 10,000 articles can take a while to process. By default, the code
points to a subset of 1,000 articles so that it runs quickly. 

I found that computing the Jaccard similarity explicitly between all 10,000 
articles requires 20 minutes on my PC, but doing it with MinHash requires a 
little under 3 minutes.

