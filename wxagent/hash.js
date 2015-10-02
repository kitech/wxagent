
P2=function(b,j){
    for(var a=[],i=0;i<j.length;i++)
        a[i%4]^=j.charCodeAt(i);
    var w=["EC","OK"],d=[];
    d[0]=b>>24&255^w[0].charCodeAt(0);
    d[1]=b>>16&255^w[0].charCodeAt(1);
    d[2]=b>>8&255^w[1].charCodeAt(0);
    d[3]=b&255^w[1].charCodeAt(1);

    w=[];
    for(i=0;i<8;i++)
        w[i]=i%2==0?a[i>>1]:d[i>>1];
    a=["0","1","2","3","4","5","6","7","8","9","A","B","C","D","E","F"];
    d="";
    for(i=0;i<w.length;i++)
        d+=a[w[i]>>4&15],d+=a[w[i]&15];
    return d
}

function friendsHash(x, K)
{
    x += "";
    for (var N = [], T = 0; T < K.length; T++)
        N[T % 4] ^= K.charCodeAt(T);
    var U = ["EC", "OK"],
    V = [];
    V[0] = x >> 24 & 255^U[0].charCodeAt(0);
    V[1] = x >> 16 & 255^U[0].charCodeAt(1);
    V[2] = x >> 8 & 255^U[1].charCodeAt(0);
    V[3] = x & 255^U[1].charCodeAt(1);
    U = [];
    for (T = 0; T < 8; T++)
        U[T] = T % 2 == 0 ? N[T >> 1] : V[T >> 1];
    N = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "A", "B", "C", "D", "E", "F"];
    V = "";
    for (T = 0; T < U.length; T++)
    {
        V += N[U[T] >> 4 & 15];
        V += N[U[T] & 15]
    }
    return V
}
