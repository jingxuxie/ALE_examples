      function dot(a,b)
      implicit none
      real(8) dot,a(4),b(4),alen,blen,an(3),bn(3),chord
      real(16) aq(3),bq(3),aqnorm,bqnorm
      alen=norm2(a(1:3))
      blen=norm2(b(1:3))
      an=a(1:3)/alen
      bn=b(1:3)/blen
      chord=sum((an-bn)**2)
      if (.true..or.chord.lt.1d-8) then
         aq=real(a(1:3),16)
         bq=real(b(1:3),16)
         aqnorm=sqrt(sum(aq**2))
         bqnorm=sqrt(sum(bq**2))
         dot=real(aqnorm*bqnorm*sum((aq/aqnorm-bq/bqnorm)**2)
     &        /2q0,8)
      else
         dot=alen*blen*chord/2d0
      endif
      end
