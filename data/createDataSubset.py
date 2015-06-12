import re

# Number of plagiarism pairs to include.
numPs = 10

# Total number of articles in dataset.
numDocs = 1000

# =============================================================================
#                  Parse The Ground Truth Tables
# =============================================================================

# Build the dictionary of all plagiarism pairings.
pDict = {}

# Build a list of plagiarism docs to include in this subset.
pInc = []

# Open the truth file.
f = open("articles_10000.truth", "rU")

# For the first 'numPs' lines...
for line in f:
  
  # Strip the newline character, if present.
  if line[-1] == '\n':
      line = line[0:-1]
      
  docs = line.split(" ")

  # Map the two documents to each other.
  pDict[docs[0]] = docs[1]
  pDict[docs[1]] = docs[0]

  # Add the documents to the list of plagiarisms to grab
  if len(pInc) < (2 * numPs):
    pInc.append(docs[0])
    pInc.append(docs[1])
    
print "Plagiarisms to grab: " + str(pInc)

# =============================================================================
#                     Grab The Plagiarism Examples
# =============================================================================

# Open the data file.
f = open("articles_10000.train", "rU")

outLines = []

# Track the number of plagiarism examples we've includedCalculate the number of non-plagiarisms to grab.
nonPs = numDocs - (numPs * 2)

# For each line in the document...
for line in f:
  # Parse line for the document ID.
  m = re.search(r't\d+', line)
  docID = m.group()
 
  # If this is one of the plagiarism examples, add it to the output.
  if docID in pInc:
    outLines.append(line)  
  # Add non-plagiarism examples until we reach our total article count.
  elif nonPs > 0 and not docID in pDict:
    outLines.append(line)
    nonPs = nonPs - 1
  
  # Break once we've built the dataset.  
  if len(outLines) == numDocs:
    break

# Close the input file.    
f.close()

# Sort the lines by document ID.

# Retrieve the integer document ID from the beginning of the line.
def nameToInt(s):
  m = re.search(r'\d+', s)
  return int(m.group())

outLines = sorted(outLines, key=nameToInt)

# Write out the lines.
filename = "articles_" + str(numDocs) + ".train"
print "Writing dataset to " + filename
f = open(filename, "w")
f.writelines(outLines)
f.close()    

# Write out the ground truth.
filename = "articles_" + str(numDocs) + ".truth"
print "Writing truth to " + filename
f = open(filename, "w")

for i in range(0, len(pInc), 2):
  # Add the pair to the truth table.
  f.write(pInc[i] + " " + pInc[i + 1] + "\n")
    
f.close()