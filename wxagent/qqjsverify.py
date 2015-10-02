#!/usr/bin/env python2

import sys
import spidermonkey

def js10113():
    # getp
    sm = spidermonkey.Runtime()
    file_js = open("wxagent/loginMd5.js", "r")
    cx = sm.new_context()
    getp = cx.execute(file_js.read())
    username = ''
    password = ''
    code1 = ''


    username = sys.argv[2]
    password = sys.argv[3]
    code1 = sys.argv[4]
    print('js10113', username, password, code1)
    p = getp(username, password, code1)
    print 'resp:', p


def js10120():
    # getp
    sm = spidermonkey.Runtime()
    file_js = open("wxagent/encrypt.js", "r")
    cx = sm.new_context()

    fulljs = 'function(password, salt, vcode) {' + \
             file_js.read() + \
             'return encryption(password, salt, vcode);}'
    # getp = cx.execute(file_js.read())
    getp = cx.execute(fulljs)
    # getp = cx.execute('function(val) {return "whoosh: " + val;}')
    password = ''
    salt = ''
    code1 = ''


    password = sys.argv[2]
    salt = sys.argv[3]
    code1 = sys.argv[4]
    print('js10120', password, salt, code1)
    p = getp(password, salt, code1)
    print 'resp:', p

    
def infoHash():
    sm = spidermonkey.Runtime()
    file_js = open("wxagent/hash.js", "r")
    cx = sm.new_context()

    fulljs = 'function(username, ptwebqq) {' + \
             file_js.read() + \
             'return P2(username, ptwebqq);}'
    # getp = cx.execute(file_js.read())
    getp = cx.execute(fulljs)
    # getp = cx.execute('function(val) {return "whoosh: " + val;}')

    username = sys.argv[2]
    ptwebqq = sys.argv[3]
    print('infohash', username, ptwebqq)
    iusername = int(username)
    p = getp(username, ptwebqq)
    print 'resphash:', p


def getHashCode(b, j):
    """
    get the hash num to achieve the grouplist info (record:gcode)
    source function:         http://0.web.qstatic.com/webqqpic/pubapps/0/50/eqq.all.js     
    source function definition:       
    P=function(b,j)          
    Args:   
        b : real QQ num  
        j : ptwebqq (get it by cookies)  
    Returns:          string : hashValue      
    Raises:          No raises      
    Author:          zhang      
    Date:          2015-7-31 
    """

    a = [0,0,0,0]
    for i in range(0,len(j)):
        a[i%4] ^= ord(j[i])
        
    w = ["EC","OK"]
    d = [0,0,0,0]
    d[0] = int(b) >> 24 & 255 ^ ord(w[0][0])
    d[1] = int(b) >> 16 & 255 ^ ord(w[0][1])
    d[2] = int(b) >> 8 & 255 ^ ord(w[1][0])
    d[3] = int(b) & 255 ^ ord(w[1][1])
    
    w = [0,0,0,0,0,0,0,0]
    for i in range(0,8):
        if i%2 == 0:
            w[i] = a[i>>1]
        else:
            w[i] = d[i>>1]

    a = ["0","1","2","3","4","5","6","7","8","9","A","B","C","D","E","F"]
    d = ""
    for i in range(0,len(w)):
        d += a[w[i]>>4&15]
        d += a[w[i]&15]
            
    return d


# if __name__ == "__main__":
#     b = "1958317603"
#     j = "8bb6208103fb248b333db1a17c7c688297379b614f6e48123cbee0d5d6a53160"
#     hashV = getHashCode(b,j)
#     print hashV


def hash(selfuin, ptwebqq):
    selfuin += ""
    N=[0,0,0,0]
    for T in range(len(ptwebqq)):
        N[T%4]=N[T%4]^int(ord(ptwebqq[T]))
    U=["EC","OK"]
    V=[0, 0, 0, 0]
    V[0]=int(selfuin) >> 24 & 255 ^ ord(U[0][0])
    V[1]=int(selfuin) >> 16 & 255 ^ ord(U[0][1])
    V[2]=int(selfuin) >>  8 & 255 ^ ord(U[1][0])
    V[3]=int(selfuin)       & 255 ^ ord(U[1][1])
    U=[0,0,0,0,0,0,0,0]
    U[0]=N[0]
    U[1]=V[0]
    U[2]=N[1]
    U[3]=V[1]
    U[4]=N[2]
    U[5]=V[2]
    U[6]=N[3]
    U[7]=V[3]  
    N=["0","1","2","3","4","5","6","7","8","9","A","B","C","D","E","F"]
    V=""
    for T in range(len(U)):
        V+= N[ U[T]>>4 & 15]
        V+= N[ U[T]    & 15]
    return V

#-----Test------------
#testHashValue = hash ("752584911", "123456789")
#print testHashValue

if sys.argv[1] == 'jsverify':
    js10120()
elif sys.argv[1] == 'infohash':
    infoHash()
    # hashval = getHashCode(sys.argv[2], sys.argv[3])
    # hashval = hash(sys.argv[2], sys.argv[3])
    # print 'resphash:', hashval
else:
    print 'resp: unknown command'

