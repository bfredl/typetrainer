#!/usr/bin/env python3
import curses
import random
from itertools import repeat
from operator import itemgetter
import pickle
import time
from math import ceil
from collections import defaultdict
import locale
locale.setlocale(locale.LC_ALL, '')
code = locale.getpreferredencoding()

def str2codes(string):
    return [ord(x) for x in string]

def codes2str(codes):
    return ''.join(chr(x) for x in codes)


lower = codes2str(range(ord('a'),ord('z')+1))
capital = codes2str(range(ord('A'),ord('Z')+1))

homerow = "aoeuidhtns"
digits = "0123456789"
raised = "!@#$%^&*(){}[]'\"=+\\|-_?.,;:~"
paran = "()67890^"
suedoise = "åÅäÄöÖ"

#charset = 3*homerow+4*lower+capital+2*digits+raised+4*paran+suedoise 
charset = 3*homerow+4*lower+2*capital+2*digits+raised#+4*paran+suedoise

def cycle(string, ch, maxlen): 
    """ 
    Adds ch to front of string,
    discarding char at end of string if too long
    """
    string = ch + string
    if len(string) > maxlen:
        string = string[:maxlen]
    return string

price = 3
linelen = 15
inital_miss = 0.3

class Scores:
    def __init__(self):
        self.misses = defaultdict(int)
        self.attempts = defaultdict(int) 
        self.hitline = defaultdict(str)
        self.highscore = 1000.0
        
    def __setstate__(self,dict):
        self.__init__()
        self.__dict__.update(dict)

    def add_hit(self,ch,misses):
        self.attempts[ch] += 1
        self.misses[ch] += misses
        hitchr = str(min(misses,9))
        self.hitline[ch] = cycle(self.hitline[ch], hitchr, linelen)

    def game_score(self, score):
        if self.highscore > score:
            self.highscore = score

    def get_misscount(self):
        misses = {}
        for char in set(charset):
            ch = ord(char)
            hitline = cycle(self.hitline[ch], "", linelen)
            misses[ch] = sum(int(x) for x in hitline)+ceil(inital_miss*(linelen-len(hitline)))
        return sorted(misses.items(),key=itemgetter(1),reverse=True)

    def get_worst(self):
        ratio = { ch: misses/(self.attempts.get(ch,1)+1.0) for (ch,misses) in self.misses.items()}
        return sorted(ratio.items(),key=itemgetter(1),reverse=True)

    def display(self, scr):
        scr.addstr(15,5, "highscore: {:.5}".format(self.highscore))
        worst = self.get_misscount()
        worststr = "".join(chr(e) for (e,_) in worst) 
        scr.addstr(16,5,worststr[:min(20,len(worststr))])

    
class game:
    def __init__(self, screen, scores):
        self.scr = screen
        self.scores = scores

    def line(self,ypos, msg):
        self.scr.addstr(10+ypos,5,msg)

    def getch(self,*a): # utf-8 > unicode HAX
        ch = self.scr.getch(*a)
        if not 127 < ch < 256:
            return ch
        ch2 = self.scr.getch(*a)
        if not 127 < ch2 < 256:
            self.scr.ungetch(ch2)
            return ch
        return ord(bytes((ch,ch2)).decode(code))

    def update(self):
        self.line(0,"misses: {}".format(self.misses))
        t = time.time() - self.tstart
        self.line(1,"time: {}".format(int(t)))
        score = t+price*self.misses
        if self.typed > 0:
            self.spc = score/self.typed
            self.line(2,"spc: {:.3f}".format(self.spc))

    def genline(self, length):
        charseq = []
        for ch, misses in self.scores.get_misscount():
            charseq.extend((misses+1)*chr(ch))
        def choose_char():
            if random.random() < 0.5:
                return random.choice(charset)
            else:
                return random.choice(charseq)
        return ''.join(choose_char() for _ in range(length))


    def runline(self, line):
        x,y = 3,1
        self.scr.addstr(y+1,x,line)
        pos = 0
        for pos,char in enumerate(line):
            charmiss = 0
            ch = ord(char)
            while True:
                self.update()
                trych = self.getch(y,x+pos)
                if trych == 3: 
                    return False
                elif trych == ch:
                    break
                else:
                    self.misses +=1
                    charmiss +=1

            self.typed += 1
            self.scores.add_hit(ch,charmiss)
        self.update()

    def run_game(self):
        self.scores.display(self.scr)
        self.tstart = time.time()
        self.misses = 0
        self.typed = 0
        for x in range(4):
            self.runline(self.genline(30))
        self.scores.game_score(self.spc)
        self.scores.display(self.scr)
        self.scr.getch()

def main(scr):
    filename = "typing_scores"
    global scores
    try:
        scores = pickle.load(open(filename,'rb'))
    except Exception:
        scores = Scores()

    char = None
    try:
        game(scr,scores).run_game()
    finally:
        pickle.dump(scores,open(filename,'wb'))

#from IPython import embed
#embed()
try:
    curses.wrapper(main)
finally:

    print([(chr(x), y) for (x,y) in scores.get_misscount()])

