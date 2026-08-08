from html.parser import HTMLParser

class MyHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        
    def handle_starttag(self, tag, attrs):
        if tag in ['div', 'span', 'h4', 'h5', 'p', 'i', 'button', 'canvas']:
            self.tags.append(tag)
            
    def handle_endtag(self, tag):
        if tag in ['div', 'span', 'h4', 'h5', 'p', 'i', 'button', 'canvas']:
            if not self.tags:
                print(f"Error: Found closing tag </{tag}> but stack is empty!")
            else:
                last_tag = self.tags.pop()
                if last_tag != tag:
                    print(f"Error: Mismatched tag. Expected </{last_tag}> but got </{tag}>.")
                    
parser = MyHTMLParser()
with open('app/templates/components/timeline.html', 'r', encoding='utf-8') as f:
    parser.feed(f.read())

if parser.tags:
    print(f"Unclosed tags at end of file: {parser.tags}")
else:
    print("All tags matched perfectly!")
