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
raised = "!@#$%^&*(){}[]<>'\"=+\\|/-_?.,;:~"
ctrls = " \n" + ''.join(chr(ord(x)-ord("A")+1) for x in "ABDEFGKLNOPRTUVXY") # FIXME: <c-h> vs <bs>
paran = "()67890^"
suedoise = "åÅäÄöÖüÜß" # NB: special cased to be colored
hints = { "$": "s-,", "^": "s-.", "%": "A-,", "^": "A-.",
        "Ä": "+\\?", "Å":"P,*", "Ö": "`'1", "f": "e+t", "F": "e+h"}

#charset = 3*homerow+4*lower+capital+2*digits+raised+4*paran+suedoise
basechars = 3*homerow+4*lower+2*capital+2*digits+raised+ctrls+suedoise
charset = set(basechars)

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
decay = 0.2
initial_val = 0.5

class Returner:
    def __init__(self, val):
        self.val = val
    def __call__(self):
        return self.val


class Scores:
    def __init__(self):
        self.misses = defaultdict(int)
        self.attempts = defaultdict(int) 
        # weighted sliding average of misses per attempt
        self.wh_avg = defaultdict(lambda: initial_val)
        self.highscore = 1000.0
        
    def __setstate__(self,dic):
        self.__dict__.update(dic)
        self.wh_avg = defaultdict(lambda: initial_val)
        self.wh_avg.update(dic["wh_avg"])

    def __getstate__(self):
        dic = self.__dict__.copy()
        dic["wh_avg"] = dict(self.wh_avg)
        return dic

    def add_hit(self,ch,misses):
        self.attempts[ch] += 1
        self.misses[ch] += misses
        self.wh_avg[ch] = (1-decay)*self.wh_avg[ch]+decay*misses

    def game_score(self, score):
        if self.highscore > score:
            self.highscore = score

    def get_misscount(self):
        misses = [(ch, self.wh_avg[ch]) for ch in charset]
        return sorted(misses,key=itemgetter(1),reverse=True)

    def get_worst(self):
        ratio = { ch: misses/(self.attempts.get(ch,1)+1.0) for (ch,misses) in self.misses.items()}
        return sorted(ratio.items(),key=itemgetter(1),reverse=True)

    def display(self, scr):
        scr.addstr(15,5, "highscore: {:.5}".format(self.highscore))
        worst = self.get_misscount()
        worststr = "".join(e for (e,_) in worst) 
        scr.addstr(16,5,worststr[:min(20,len(worststr))])

    
class game:
    def __init__(self, screen, scores):
        self.scr = screen
        self.scores = scores

    def line(self,xpos, ypos, msg):
        for char in msg:
            attr = curses.A_NORMAL
            extra = " "
            if char == "\n":
                char = " "
                attr = curses.color_pair(2)
            elif char == " ":
                attr = curses.A_STANDOUT
            elif ord(char) < ord(" "):
                char = chr(ord(char)-1+ord("A"))
                attr = curses.color_pair(1)
                extra = "C"
            elif char in suedoise:
                attr = curses.color_pair(3)
            self.scr.addstr(ypos,xpos,char,attr)
            self.scr.addstr(ypos-1,xpos,extra, curses.A_NORMAL)
            xpos += 1

    def getch(self,*a): # utf-8 > unicode HAX
        ch = self.scr.getch(*a)
        if not 127 < ch < 256:
            return ch
        ch2 = self.scr.getch(*a)
        if not 127 < ch2 < 256:
            self.scr.ungetch(ch2)
            return ch
        try:
            return ord(bytes((ch,ch2)).decode(code))
        except UnicodeDecodeError:
            return "�"

    def update(self):
        self.scr.addstr(10, 5,"misses: {}".format(self.misses))
        t = time.time() - self.tstart
        self.scr.addstr(11, 5,"time: {}".format(int(t)))
        score = t+price*self.misses
        if self.typed > 0:
            self.spc = score/self.typed
            self.scr.addstr(12, 5,"spc: {:.3f}".format(self.spc))

    def genline(self, length):
        charseq = []
        for ch, misses in self.scores.get_misscount():
            charseq.extend(int(20*misses)*ch)
        def choose_char():
            if random.random() < 0.5:
                return random.choice(basechars)
            else:
                return random.choice(charseq)
        return ''.join(choose_char() for _ in range(length))

    def hint(self, ch):
        hint = "x-x"
        if ch in hints:
            hint = hints[ch]
        elif ord(ch) < ord(" "):
            hint = "C-" + chr(ord(ch)-1+ord("A"))
        self.scr.addstr(8, 5, "protip: " + hint)


    def runline(self, line):
        x,y = 3,1
        self.line(3,2,line)
        pos = 0
        for pos,char in enumerate(line):
            charmiss = 0
            ch = ord(char)
            self.hint("x")
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
                    self.hint(char)

            self.typed += 1
            self.scores.add_hit(char,charmiss)
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
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1,0,2)
    curses.init_pair(2,0,1)
    curses.init_pair(3,2,-1)
    filename = "typing_scores"
    global scores
    try:
        scores = pickle.load(open(filename,'rb'))
    except Exception:
        scores = Scores()

    try:
        game(scr,scores).run_game()
    finally:

        from IPython import embed
        pickle.dump(scores,open(filename,'wb'))

try:
    curses.wrapper(main)
finally:
    print([(x, y) for (x,y) in scores.get_misscount()])

