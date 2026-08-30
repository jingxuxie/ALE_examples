      subroutine rotatetoz(a,rmat)
      implicit real*8(a-h,o-z)
      dimension a(4),b(4),rmat(4,4),rmatz(4,4),rmaty(4,4)
      parameter(pi=3.141592653589793238d0)
      if(a(1).eq.0d0.and.a(2).eq.0d0.and.a(3).ge.0d0) then
         do i=1,4
            do j=1,4
               rmat(i,j) = 0d0
            enddo
            rmat(i,i) = 1d0
         enddo
         return
      endif

      rmatz(4,4) = 1d0
      do i=1,3
         rmatz(4,i) = 0d0
         rmatz(i,4) = 0d0
      enddo

      if(a(1).eq.0d0) then
         rmatz(1,1) = 0d0
         rmatz(1,2) = 1d0
         rmatz(2,1) = -1d0
         rmatz(2,2) = 0d0
      else
         cphiz = 1d0/dsqrt(1+(a(2)/a(1))**2) !cos(arctan(a2/a1))
         sphiz = (a(2)/a(1))/dsqrt(1+(a(2)/a(1))**2)!sin(arctan(a2/a1))
         rmatz(1,1) = cphiz
         rmatz(1,2) = sphiz
         rmatz(2,1) = -sphiz
         rmatz(2,2) = cphiz
      endif
      rmatz(3,3) = 1d0
      do i=1,2
         rmatz(i,3) = 0d0
         rmatz(3,i) = 0d0
      enddo

      do i=1,4
         b(i)=0d0
         do j=1,4
            b(i)=b(i) + rmatz(i,j)*a(j)
         enddo
      enddo

      rmaty(4,4) = 1d0
      do i=1,3
         rmaty(4,i) = 0d0
         rmaty(i,4) = 0d0
      enddo

      if(b(3).eq.0d0) then
         b00 = 1d0
         if (b(1).le.0d0) b00 = -1d0 
         rmaty(1,1) = 0d0
         rmaty(1,3) = -b00
         rmaty(3,1) = b00
         rmaty(3,3) = 0d0
      else
         cphiy = 1d0/dsqrt(1+(b(1)/b(3))**2) !cos(arctan(a2/a1))
         sphiy = (b(1)/b(3))/dsqrt(1+(b(1)/b(3))**2) !sin(arctan(a2/a1))
         if(b(3).lt.0d0) then
            cphiy=-cphiy
            sphiy=-sphiy
         endif
         rmaty(1,1) = cphiy
         rmaty(1,3) = -sphiy
         rmaty(3,1) = sphiy
         rmaty(3,3) = cphiy
      endif
      rmaty(2,2) = 1d0
      do i=1,3,2
         rmaty(i,2) = 0d0
         rmaty(2,i) = 0d0
      enddo

      do i=1,4
         do j=1,4
            rmat(i,j) = 0d0
            do k=1,4
               rmat(i,j) = rmat(i,j) + rmaty(i,k)*rmatz(k,j)
            enddo
         enddo
      enddo

      return
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
