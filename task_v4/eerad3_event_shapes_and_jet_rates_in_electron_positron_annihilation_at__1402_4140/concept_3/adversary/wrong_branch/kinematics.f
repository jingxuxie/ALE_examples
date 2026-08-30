      subroutine pmap5to3(i1,i2,i3,i4,i5,j1,j2,j3)
      implicit none
      integer i1,i2,i3,i4,i5,j1,j2,j3,particle,other,component
      real(8) y(5,5),p(4,5),ppar(4,5),s12,s13,s23
      real(8) p5(4,5),p4(4,4),p3(4,3)
      real(16) qp(4,5),qy(5,5),result(4,3),qs(3,3)
      real(16) factor,total,a,b,c,d
      common /yij5/y
      common /pmom/p
      common /pcut/ppar
      common /s3/s12,s13,s23
      common /mapmomenta/p5,p4,p3
      if (.true..and.y(i1,i4).gt.1d-5) then
         call pmap5to3_fast(i1,i2,i3,i4,i5,j1,j2,j3)
         return
      endif
      factor=real(maxval(abs(p)),16)
      qp=real(p,16)/factor
      do particle=1,5
         qp(4,particle)=sqrt(sum(qp(1:3,particle)**2))
      enddo
      total=sum(qp(4,:))
      do particle=1,5
         do other=1,5
            qy(particle,other)=qp(4,particle)*qp(4,other)*
     &       sum((qp(1:3,particle)/qp(4,particle)-
     &       qp(1:3,other)/qp(4,other))**2)/(total*total)
         enddo
      enddo
      call dak2_wide(qy(i1,i2),qy(i1,i3),qy(i2,i4),
     & qy(i3,i4),qy(i2,i3),qy(i1,i4),a,b,c,d)
      result(:,j1)=a*qp(:,i1)+b*qp(:,i2)+c*qp(:,i3)+d*qp(:,i4)
      result(:,j2)=(1q0-a)*qp(:,i1)+(1q0-b)*qp(:,i2)
     &            +(1q0-c)*qp(:,i3)+(1q0-d)*qp(:,i4)
      result(:,j3)=qp(:,i5)
      do particle=1,3
         do other=1,3
            qs(particle,other)=2q0*(result(4,particle)*
     &        result(4,other)-sum(result(1:3,particle)*
     &        result(1:3,other)))/(total*total)
         enddo
      enddo
      ppar(:,1:3)=real(result*factor,8)
      ppar(:,j3)=p(:,i5)
      p3=ppar(:,1:3)
      s12=real(qs(1,2),8)
      s13=real(qs(1,3),8)
      s23=real(qs(2,3),8)
      end
      subroutine pmap5to3_fast(i1,i2,i3,i4,i5,j1,j2,j3)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      common/s3/s12,s13,s23
      common/pmom/p(4,5) 
      common/pcut/ppar(4,5)
      common/mapmomenta/p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      dimension s(3,3)

      y12=y(i1,i2)
      y13=y(i1,i3)
      y14=y(i1,i4)
      y23=y(i2,i3)
      y24=y(i2,i4)
      y34=y(i3,i4)

      call DAK2(y12,y13,y24,y34,y23,y14,a,b,c,d)

      s(j1,j2)=        y(i1,i2) +y(i1,i3) +y(i1,i4)
     .                +y(i2,i3) +y(i2,i4) +y(i3,i4)
      
      s(j1,j3)=      a*y(i1,i5)      +b*y(i2,i5)      
     .              +c*y(i3,i5)      +d*y(i4,i5)
      s(j2,j3)=(1d0-a)*y(i1,i5)+(1d0-b)*y(i2,i5)
     .        +(1d0-c)*y(i3,i5)+(1d0-d)*y(i4,i5)

      s(j2,j1)=s(j1,j2)
      s(j3,j1)=s(j1,j3)
      s(j3,j2)=s(j2,j3)

      do i=1,4
         ppar(i,j1) =         a*p(i,i1) +       b*p(i,i2)      
     .                +       c*p(i,i3) +       d*p(i,i4)
         ppar(i,j2) =   (1d0-a)*p(i,i1) + (1d0-b)*p(i,i2)
     .                + (1d0-c)*p(i,i3) + (1d0-d)*p(i,i4)
         ppar(i,j3) = p(i,i5)
         p3(i,j1) = ppar(i,j1)
         p3(i,j2) = ppar(i,j2)
         p3(i,j3) = ppar(i,j3)
      enddo

      s12 = s(1,2)
      s13 = s(1,3)
      s23 = s(2,3)

      return
      end
      subroutine DAK2(ya1,ya2,y1b,y2b,y12,yab,x,r1,r2,y)
      implicit real*8(a-h,o-z)
      
      ya12b=ya1+ya2+y1b+y2b+y12+yab

      r1 = (y1b+y12)/(ya1+y1b+y12)
      r2 =       y2b/(ya2+y2b+y12)

      rho2 = 1d0
     .     +(r1-r2)**2/yab**2/ya12b**2*
     .     (yab**2*y12**2+ya1**2*y2b**2+ya2**2*y1b**2
     .     -2d0*(yab*ya1*y2b*y12+yab*ya2*y1b*y12+ya1*ya2*y1b*y2b))
     .     +((r1*(1d0-r2)+r2*(1d0-r1))
     .     *2d0*(yab*ya1*y2b+yab*ya2*y1b-yab**2*y12)
     .     +4d0*r1*(1d0-r1)*yab*ya1*y1b
     .     +4d0*r2*(1d0-r2)*yab*ya2*y2b)/yab**2/ya12b
      rho = -sqrt(rho2)
      
      
      x = 1d0/2d0/(yab+ya1+ya2)*(
     .     (1d0+rho)*ya12b
     .     -(2d0*y1b+y12)*r1
     .     -(2d0*y2b+y12)*r2
     .     +(ya1*y2b-ya2*y1b)*(r1-r2)/yab)

      y = 1d0/2d0/(yab+y1b+y2b)*(
     .     (1d0-rho)*ya12b
     .     -(2d0*ya1+y12)*r1
     .     -(2d0*ya2+y12)*r2
     .     -(ya1*y2b-ya2*y1b)*(r1-r2)/yab)

      return
      end
      subroutine dak2_wide(ya1,ya2,y1b,y2b,y12,yab,x,r1,r2,y)
      implicit real*16(a-h,o-z)
      
      ya12b=ya1+ya2+y1b+y2b+y12+yab

      r1 = (y1b+y12)/(ya1+y1b+y12)
      r2 =       y2b/(ya2+y2b+y12)

      rho2 = 1q0
     .     +(r1-r2)**2/yab**2/ya12b**2*
     .     (yab**2*y12**2+ya1**2*y2b**2+ya2**2*y1b**2
     .     -2q0*(yab*ya1*y2b*y12+yab*ya2*y1b*y12+ya1*ya2*y1b*y2b))
     .     +((r1*(1q0-r2)+r2*(1q0-r1))
     .     *2q0*(yab*ya1*y2b+yab*ya2*y1b-yab**2*y12)
     .     +4q0*r1*(1q0-r1)*yab*ya1*y1b
     .     +4q0*r2*(1q0-r2)*yab*ya2*y2b)/yab**2/ya12b
      rho = -sqrt(rho2)
      
      
      x = 1q0/2q0/(yab+ya1+ya2)*(
     .     (1q0+rho)*ya12b
     .     -(2q0*y1b+y12)*r1
     .     -(2q0*y2b+y12)*r2
     .     +(ya1*y2b-ya2*y1b)*(r1-r2)/yab)

      y = 1q0/2q0/(yab+y1b+y2b)*(
     .     (1q0-rho)*ya12b
     .     -(2q0*ya1+y12)*r1
     .     -(2q0*ya2+y12)*r2
     .     -(ya1*y2b-ya2*y1b)*(r1-r2)/yab)

      return
      end
