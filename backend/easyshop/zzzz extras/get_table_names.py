import re

### \d{1,2}. [A-z]+
def extract_matching_words(file_path, pattern):
  with open(file_path, 'r') as file:
    content = file.read()
  matches = re.findall(pattern, content)
  return matches

if __name__ == "__main__":
  file_path = '/home/suhail/Desktop/Final Project/PROJECT/Backend/easyshop/database6.md'
  pattern = r'### \d{1,2}\. [A-Za-z_]+'
  matching_words = extract_matching_words(file_path, pattern)
  for word in matching_words:
    print(word[3:])