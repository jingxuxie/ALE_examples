      subroutine rotatetoz(a,rmat)
      implicit none
      real*8 a(4),rmat(4,4),axis(3),transverse,radius
      real*8 cphi,sphi,ctheta,stheta,largest,transcale
      rmat=0d0
      rmat(4,4)=1d0
      largest=maxval(abs(a(1:3)))
      if(a(1).eq.0d0.and.a(2).eq.0d0) then
         rmat(1,1)=sign(1d0,a(3))
         rmat(2,2)=1d0
         rmat(3,3)=sign(1d0,a(3))
         return
      endif
      transcale=max(abs(a(1)),abs(a(2)))
      transverse=sqrt((a(1)/transcale)**2+
     .                (a(2)/transcale)**2)
      if(a(1).eq.0d0) then
         cphi=0d0
         sphi=1d0
      else
         cphi=abs(a(1)/transcale)/transverse
         sphi=sign(1d0,a(1))*(a(2)/transcale)/transverse
      endif
      axis=a(1:3)/largest
      radius=sqrt(sum(axis**2))
      ctheta=axis(3)/radius
      stheta=(transcale/largest)*transverse/radius
      if(a(1).ne.0d0) then
         stheta=sign(stheta,a(1))
      else
         stheta=sign(stheta,a(2))
      endif
      rmat(1,1)=ctheta*cphi
      rmat(1,2)=ctheta*sphi
      rmat(1,3)=-stheta
      rmat(2,1)=-sphi
      rmat(2,2)=cphi
      rmat(3,1)=stheta*cphi
      rmat(3,2)=stheta*sphi
      rmat(3,3)=ctheta
      end

      subroutine unrotatetoz(a,rmat)
      implicit none
      real*8 a(4),rmat(4,4),forward(4,4)
      call rotatetoz(a,forward)
      rmat=transpose(forward)
      end

      subroutine fillinv(n,p,sij)
      implicit none
      integer n,first,second,component,powers(n)
      real*8 p(4,n),sij(n,n),nullpair,vectors(3,n),norms(n)
      do first=1,n
         powers(first)=exponent(maxval(abs(p(1:3,first))))
         do component=1,3
            vectors(component,first)=scale(p(component,first),
     .                                     -powers(first))
         enddo
         norms(first)=sqrt(sum(vectors(:,first)**2))
      enddo
      do first=1,n
         sij(first,first)=0d0
         do second=first+1,n
            sij(first,second)=scale(2d0*
     .           nullpair(vectors(:,first),vectors(:,second),
     .                    norms(first),norms(second)),
     .           powers(first)+powers(second))
            sij(second,first)=sij(first,second)
         enddo
      enddo
      end
