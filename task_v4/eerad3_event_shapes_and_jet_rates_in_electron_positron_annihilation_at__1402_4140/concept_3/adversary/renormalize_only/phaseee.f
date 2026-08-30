      subroutine rotatetoz(a,rmat)
      implicit none
      real(8) a(4),rmat(4,4),scaled(3),radius,transverse
      real(8) cosine,sine,polarcos,polarsin,largest
      rmat=0d0
      rmat(4,4)=1d0
      largest=maxval(abs(a(1:3)))
      if (largest.eq.0d0) then
         rmat(1,1)=1d0
         rmat(2,2)=1d0
         rmat(3,3)=1d0
         return
      endif
      scaled=a(1:3)/largest
      radius=norm2(scaled)
      transverse=norm2(scaled(1:2))
      if (transverse.eq.0d0.and.scaled(3).ge.0d0) then
         rmat(1,1)=1d0
         rmat(2,2)=1d0
         rmat(3,3)=1d0
         return
      endif
      if (scaled(1).eq.0d0) then
         cosine=0d0
         sine=1d0
      else
         cosine=abs(scaled(1))/transverse
         sine=sign(1d0,scaled(1))*scaled(2)/transverse
      endif
      polarcos=scaled(3)/radius
      polarsin=(cosine*scaled(1)+sine*scaled(2))/radius
      rmat(1,1)=polarcos*cosine
      rmat(1,2)=polarcos*sine
      rmat(1,3)=-polarsin
      rmat(2,1)=-sine
      rmat(2,2)=cosine
      rmat(3,1)=polarsin*cosine
      rmat(3,2)=polarsin*sine
      rmat(3,3)=polarcos
      end
      subroutine unrotatetoz(a,rmat)
      implicit real*8(a-h,o-z)
      dimension a(4),b(4),rmat(4,4),rmatinv(4,4)
      call rotatetoz(a,rmatinv)
      do i=1,4
         do j=1,4
            rmat(i,j)=rmatinv(j,i)
         enddo
      enddo
      return
      end
      subroutine fillinv(n,p,sij)
      implicit real*8(a-h,o-z)
      dimension p(4,1:n),sij(1:n,1:n)
      do i=1,n
         sij(i,i) = 0d0
         do j=i+1,n
            sij(i,j) = 2d0*dot(p(1,i),p(1,j))
            sij(j,i) = sij(i,j)
         enddo
      enddo
      return
      end
