# ======== runMinHashExample =======
# This example code demonstrates comparing documents using the MinHash
# approach. 
#
# First, each document is represented by the set of shingles it contains. The
# documents can then be compared using the Jaccard similarity of their 
# shingle sets. This is computationally expensive, however, for large numbers
# of documents. 
#
# For comparison, we will also use the MinHash algorithm to calculate short 
# signature vectors to represent the documents. These MinHash signatures can 
# then be compared quickly by counting the number of components in which the 
# signatures agree. We'll compare all possible pairs of documents, and find 
# the pairs with high similarity.
#
# The program follows these steps:
# 1. Convert each test file into a set of shingles.
#    - The shingles are formed by combining three consecutive words together.
#    - Shingles are mapped to shingle IDs using the CRC32 hash.
# 2. Calculate all Jaccard similarities directly.
#    - This is ok for small dataset sizes. For the full 10,000 articles, it
#      takes 20 minutes!
# 3. Calculate the MinHash signature for each document.
#    - The MinHash algorithm is implemented using the random hash function 
#      trick which prevents us from having to explicitly compute random
#      permutations of all of the shingle IDs. For further explanation, see
#      section 3.3.5 of http://infolab.stanford.edu/~ullman/mmds/ch3.pdf
# 4. Compare all MinHash signatures to one another.
#    - Compare MinHash signatures by counting the number of components in which
#      the signatures are equal. Divide the number of matching components by
#      the signature length to get a similarity value.
#    - Display pairs of documents / signatures with similarity greater than a
#      threshold.

from __future__ import division
import os
import re
import random
import time
import binascii
from bisect import bisect_right
from heapq import heappop, heappush

# This is the number of components in the resulting MinHash signatures.
# Correspondingly, it is also the number of random hash functions that
# we will need in order to calculate the MinHash.
numHashes = 10;

# You can run this code for different portions of the dataset.
# It ships with data set sizes 100, 1000, 2500, and 10000.
numDocs = 1000
dataFile = "./data/articles_" + str(numDocs) + ".train"
truthFile = "./data/articles_" + str(numDocs) + ".truth"

# =============================================================================
#                  Parse The Ground Truth Tables
# =============================================================================
# Build a dictionary mapping the document IDs to their plagiaries, and vice-
# versa.
plagiaries = {}

# Open the truth file.
f = open(truthFile, "rU")

# For each line of the files...
for line in f:
  
  # Strip the newline character, if present.
  if line[-1] == '\n':
      line = line[0:-1]
      
  docs = line.split(" ")

  # Map the two documents to each other.
  plagiaries[docs[0]] = docs[1]
  plagiaries[docs[1]] = docs[0]

# =============================================================================
#               Convert Documents To Sets of Shingles
# =============================================================================

print "Shingling articles..."

# The current shingle ID value to assign to the next new shingle we 
# encounter. When a shingle gets added to the dictionary, we'll increment this
# value.
curShingleID = 0

# Create a dictionary of the articles, mapping the article identifier (e.g., 
# "t8470") to the list of shingle IDs that appear in the document.
docsAsShingleSets = {};
  
# Open the data file.
f = open(dataFile, "rU")

docNames = []

t0 = time.time()

totalShingles = 0

for i in range(0, numDocs):
  
  # Read all of the words (they are all on one line) and split them by white
  # space.
  words = f.readline().split(" ") 
  
  # Retrieve the article ID, which is the first word on the line.  
  docID = words[0]
  
  # Maintain a list of all document IDs.  
  docNames.append(docID)
    
  del words[0]  
  
  # 'shinglesInDoc' will hold all of the unique shingle IDs present in the 
  # current document. If a shingle ID occurs multiple times in the document,
  # it will only appear once in the set (this is a property of Python sets).
  shinglesInDoc = set()
  
  # For each word in the document...
  for index in range(0, len(words) - 2):
    # Construct the shingle text by combining three words together.
    shingle = words[index] + " " + words[index + 1] + " " + words[index + 2]

    # Hash the shingle to a 32-bit integer.
    crc = binascii.crc32(shingle) & 0xffffffff
    
    # Add the hash value to the list of shingles for the current document. 
    # Note that set objects will only add the value to the set if the set 
    # doesn't already contain it. 
    shinglesInDoc.add(crc)
  
  # Store the completed list of shingles for this document in the dictionary.
  docsAsShingleSets[docID] = shinglesInDoc
  
  # Count the number of shingles across all documents.
  totalShingles = totalShingles + (len(words) - 2)

# Close the data file.  
f.close()  

# Report how long shingling took.
print '\nShingling ' + str(numDocs) + ' docs took %.2f sec.' % (time.time() - t0)
 
print '\nAverage shingles per doc: %.2f' % (totalShingles / numDocs)

# =============================================================================
#                     Define Triangle Matrices
# =============================================================================

# Define virtual Triangle matrices to hold the similarity values. For storing
# similarities between pairs, we only need roughly half the elements of a full
# matrix. Using a triangle matrix requires less than half the memory of a full
# matrix, and can protect the programmer from inadvertently accessing one of
# the empty/invalid cells of a full matrix.

# Calculate the number of elements needed in our triangle matrix
numElems = int(numDocs * (numDocs - 1) / 2)

# Initialize two empty lists to store the similarity values. 
# 'JSim' will be for the actual Jaccard Similarity values. 
# 'estJSim' will be for the estimated Jaccard Similarities found by comparing
# the MinHash signatures.
JSim = [0 for x in range(numElems)]
estJSim = [0 for x in range(numElems)]

# Define a function to map a 2D matrix coordinate into a 1D index.
def getTriangleIndex(i, j):
  # If i == j that's an error.
  if i == j:
    sys.stderr.write("Can't access triangle matrix with i == j")
    sys.exit(1)
  # If j < i just swap the values.
  if j < i:
    temp = i
    i = j
    j = temp
  
  # Calculate the index within the triangular array.
  # This fancy indexing scheme is taken from pg. 211 of:
  # http://infolab.stanford.edu/~ullman/mmds/ch6.pdf
  # But I adapted it for a 0-based index.
  # Note: The division by two should not truncate, it
  #       needs to be a float. 
  k = int(i * (numDocs - (i + 1) / 2.0) + j - i) - 1
  
  return k


# =============================================================================
#                 Calculate Jaccard Similarities
# =============================================================================
# In this section, we will directly calculate the Jaccard similarities by 
# comparing the sets. This is included here to show how much slower it is than
# the MinHash approach.

# Calculating the Jaccard similarities gets really slow for large numbers
# of documents.
if numDocs <= 2500:
#if True:
    print "\nCalculating Jaccard Similarities..."

    # Time the calculation.
    t0 = time.time()

    # For every document pair...
    for i in range(0, numDocs):
      
      # Print progress every 100 documents.
      if (i % 100) == 0:
        print "  (" + str(i) + " / " + str(numDocs) + ")"

      # Retrieve the set of shingles for document i.
      s1 = docsAsShingleSets[docNames[i]]
      
      for j in range(i + 1, numDocs):
        # Retrieve the set of shingles for document j.
        s2 = docsAsShingleSets[docNames[j]]
        
        # Calculate and store the actual Jaccard similarity.
        JSim[getTriangleIndex(i, j)] = (len(s1.intersection(s2)) / len(s1.union(s2)))    

    # Calculate the elapsed time (in seconds)
    elapsed = (time.time() - t0)
        
    print "\nCalculating all Jaccard Similarities took %.2fsec" % elapsed

# Delete the Jaccard Similarities, since it's a pretty big matrix.    
del JSim
        
# =============================================================================
#                 Generate MinHash Signatures
# =============================================================================

# Time this step.
t0 = time.time()

print '\nGenerating random hash functions...'

# Record the maximum shingle ID that we assigned.
maxShingleID = 2**32-1

# We need the next largest prime number above 'maxShingleID'.
# I looked this value up here: 
# http://compoasso.free.fr/primelistweb/page/prime/liste_online_en.php
nextPrime = 4294967311


# Our random hash function will take the form of:
#   h(x) = (a*x + b) % c
# Where 'x' is the input value, 'a' and 'b' are random coefficients, and 'c' is
# a prime number just greater than maxShingleID.

# Generate a list of 'k' random coefficients for the random hash functions,
# while ensuring that the same value does not appear multiple times in the 
# list.
def pickRandomCoeffs(k):
  # Create a list of 'k' random values.
  randList = []
  
  while k > 0:
    # Get a random shingle ID.
    randIndex = random.randint(0, maxShingleID) 
  
    # Ensure that each random number is unique.
    while randIndex in randList:
      randIndex = random.randint(0, maxShingleID) 
    
    # Add the random number to the list.
    randList.append(randIndex)
    k = k - 1
    
  return randList

# For each of the 'numHashes' hash functions, generate a different coefficient 'a' and 'b'.   
coeffA = pickRandomCoeffs(numHashes)
coeffB = pickRandomCoeffs(numHashes)

print '\nGenerating MinHash signatures for all documents...'

# List of documents represented as signature vectors
signatures = []

# Rather than generating a random permutation of all possible shingles, 
# we'll just hash the IDs of the shingles that are *actually in the document*,
# then take the lowest resulting hash code value. This corresponds to the index 
# of the first shingle that you would have encountered in the random order.

# For each document...
for docID in docNames:
  
  # Get the shingle set for this document.
  shingleIDSet = docsAsShingleSets[docID]
  
  # The resulting minhash signature for this document. 
  signature = []
  
  # For each of the random hash functions...
  for i in range(0, numHashes):
    
    # For each of the shingles actually in the document, calculate its hash code
    # using hash function 'i'. 
    
    # Track the lowest hash ID seen. Initialize 'minHashCode' to be greater than
    # the maximum possible value output by the hash.
    minHashCode = nextPrime + 1
    
    # For each shingle in the document...
    for shingleID in shingleIDSet:
      # Evaluate the hash function.
      hashCode = (coeffA[i] * shingleID + coeffB[i]) % nextPrime 
      
      # Track the lowest hash code seen.
      if hashCode < minHashCode:
        minHashCode = hashCode

    # Add the smallest hash code value as component number 'i' of the signature.
    signature.append(minHashCode)
  
  # Store the MinHash signature for this document.
  signatures.append(signature)

# Calculate the elapsed time (in seconds)
elapsed = (time.time() - t0)
        
print "\nGenerating MinHash signatures took %.2fsec" % elapsed  

# =============================================================================
#                     Compare All Signatures
# =============================================================================  

print '\nComparing all signatures...'  
  
# Creates a N x N matrix initialized to 0.

# Time this step.
t0 = time.time()

# For each of the test documents...
for i in range(0, numDocs):
  # Get the MinHash signature for document i.
  signature1 = signatures[i]
    
  # For each of the other test documents...
  for j in range(i + 1, numDocs):
    
    # Get the MinHash signature for document j.
    signature2 = signatures[j]
    
    count = 0
    # Count the number of positions in the minhash signature which are equal.
    for k in range(0, numHashes):
      count = count + (signature1[k] == signature2[k])
    
    # Record the percentage of positions which matched.    
    estJSim[getTriangleIndex(i, j)] = (count / numHashes)

# Calculate the elapsed time (in seconds)
elapsed = (time.time() - t0)
        
print "\nComparing MinHash signatures took %.2fsec" % elapsed  
    
    
# =============================================================================
#                   Display Similar Document Pairs
# =============================================================================  

# Count the true positives and false positives.
tp = 0
fp = 0
  
threshold = 0.5  
print "\nList of Document Pairs with J(d1,d2) more than", threshold
print "Values shown are the estimated Jaccard similarity and the actual"
print "Jaccard similarity.\n"
print "                   Est. J   Act. J"

# For each of the document pairs...
for i in range(0, numDocs):  
  for j in range(i + 1, numDocs):
    # Retrieve the estimated similarity value for this pair.
    estJ = estJSim[getTriangleIndex(i, j)]
    
    # If the similarity is above the threshold...
    if estJ > threshold:
    
      # Calculate the actual Jaccard similarity for validation.
      s1 = docsAsShingleSets[docNames[i]]
      s2 = docsAsShingleSets[docNames[j]]
      J = (len(s1.intersection(s2)) / len(s1.union(s2)))
      
      # Print out the match and similarity values with pretty spacing.
      print "  %5s --> %5s   %.2f     %.2f" % (docNames[i], docNames[j], estJ, J)
      
      # Check whether this is a true positive or false positive.
      # We don't need to worry about counting the same true positive twice
      # because we implemented the for-loops to only compare each pair once.
      if plagiaries[docNames[i]] == docNames[j]:
        tp = tp + 1
      else:
        fp = fp + 1

# Display true positive and false positive counts.
print
print "True positives:  " + str(tp) + " / " + str(int(len(plagiaries.keys()) / 2))
print "False positives: " + str(fp)
