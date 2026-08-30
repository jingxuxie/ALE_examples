* momentum maps and subtraction terms for double unresolved double real radiation
* equation numbers refer to arXiv:0710.0346
************************************************************************
*
c---- momentum maps
      subroutine pmap5to3(i1,i2,i3,i4,i5,j1,j2,j3)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      common /s3/s12,s13,s23
      common /pmom/p(4,5) 
      common /pcut/ppar(4,5) 
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
        ppar(i,j1)=      a*p(i,i1)      +b*p(i,i2)      
     .                  +c*p(i,i3)      +d*p(i,i4)
     
        ppar(i,j2)=(1d0-a)*p(i,i1)+(1d0-b)*p(i,i2)
     .            +(1d0-c)*p(i,i3)+(1d0-d)*p(i,i4)
     
        ppar(i,j3)=p(i,i5)
      enddo
      s12=s(1,2)
      s13=s(1,3)
      s23=s(2,3)
      test=y12+y13+y14+y23+y24+y34

      return
      end
*
************************************************************************
*
      subroutine DAK2(ya1,ya2,y1b,y2b,y12,yab,x,r1,r2,y)
      implicit real*8(a-h,o-z)
      
      ya12b=ya1+ya2+y1b+y2b+y12+yab

      r1 = (y1b+y12)/(ya1+y1b+y12)
      r2 =       y2b/(ya2+y2b+y12)

      rho2 = 1d0
     .  +(r1-r2)**2/yab**2/ya12b**2*
     .  (yab**2*y12**2+ya1**2*y2b**2+ya2**2*y1b**2
     . -2d0*(yab*ya1*y2b*y12+yab*ya2*y1b*y12+ya1*ya2*y1b*y2b))
     .  +((r1*(1d0-r2)+r2*(1d0-r1))
     . *2d0*(yab*ya1*y2b+yab*ya2*y1b-yab**2*y12)
     .  +4d0*r1*(1d0-r1)*yab*ya1*y1b
     .  +4d0*r2*(1d0-r2)*yab*ya2*y2b)/yab**2/ya12b
      rho=sqrt(rho2)
      
      
      x=1d0/2d0/(yab+ya1+ya2)*(
     .   (1d0+rho)*ya12b
     .     -(2d0*y1b+y12)*r1
     .     -(2d0*y2b+y12)*r2
     .   +(ya1*y2b-ya2*y1b)*(r1-r2)/yab)
     
      y=1d0/2d0/(yab+y1b+y2b)*(
     .   (1d0-rho)*ya12b
     .     -(2d0*ya1+y12)*r1
     .     -(2d0*ya2+y12)*r2
     .   -(ya1*y2b-ya2*y1b)*(r1-r2)/yab)
       return
       end
       
*
************************************************************************
      subroutine pmap5to4to3(i1,i2,i3,i4,i5,j1,j2,j3)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      common /sa3/y14,y12,y24
      common /sb3/wl1l3,wl1l2,wl2l3
      common /sc3/s12,s13,s23
      common /pmom/p(4,5) 
      common /pcut/ppar(4,5) 
      common /tcuts/ymin,y0
      common/mapmomenta/p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      dimension s(3,3)

      do i=1,4
         p5(i,1) = p(i,i1)
         p5(i,2) = p(i,i2)
         p5(i,3) = p(i,i3)
         p5(i,4) = p(i,i4)
         p5(i,5) = p(i,i5)
      enddo

      y12=y(i1,i2)
      y14=y(i1,i4)
      y24=y(i2,i4)

* first i2 unresolved, i1,i4 radiators

      call DAK(y12,y24,y14,a1,b1,c1)

      wl1l3=         y(i1,i2)         +y(i1,i4)         +y(i2,i4)
      wl1l2=      a1*y(i1,i3)      +b1*y(i2,i3)      +c1*y(i4,i3)
      wl2l3=(1d0-a1)*y(i1,i3)+(1d0-b1)*y(i2,i3)+(1d0-c1)*y(i4,i3)
          
*     l1=a1*pi1+b1*pi2+c1*pi4
*     l3=(1-a1)*pi1+(1-b1)*pi2+(1-c1)*pi4
*     l2=pi3
*     l4=pi5
*     w14=wl1l3,w13=wl1l2,w34=wl2l3

      do i=1,4
         p4(i,1) = a1*p(i,i1) + b1*p(i,i2) + c1*p(i,i4)
         p4(i,3) = (1d0-a1)*p(i,i1) + (1d0-b1)*p(i,i2) 
     .            +(1d0-c1)*p(i,i4)
         p4(i,2) = p(i,i3)
         p4(i,4) = p(i,i5)
      enddo

*  now l2 unresolved, l1,l3 radiators

      call DAK(wl1l2,wl2l3,wl1l3,a2,b2,c2)
      
      a=a2*a1+c2*(1d0-a1)
      b=a2*b1+c2*(1d0-b1)
      c=b2
      d=a2*c1+c2*(1d0-c1)
      
*      j1=a2*l1+b2*l2+c2*l3=a*pi1+b*pi2+c*pi3+d*pi4
*      j2=(1-a2)*l1+(1-b2)*l2+(1-c2)*l3=
*        (1-a)*pi1+(1-b)*pi2+(1-c)*pi3+(1-d)*pi4
*      j3=l4=pi5
*      
      s(j1,j3)= a*y(i1,i5)+b*y(i2,i5)   
     .         +c*y(i3,i5)+d*y(i4,i5)
      s(j2,j3)=(1d0-a)*y(i1,i5) +(1d0-b)*y(i2,i5)    
     .        +(1d0-c)*y(i3,i5) + (1d0-d)*y(i4,i5)
      s(j1,j2)= y(i1,i2)+y(i1,i3)+y(i1,i4)+y(i2,i3)+y(i2,i4)+y(i3,i4)
      
      do i=1,4
        ppar(i,j1)=      a*p(i,i1)      +b*p(i,i2)
     .          	+c*p(i,i3)      +d*p(i,i4)
        ppar(i,j2)=(1d0-a)*p(i,i1)+(1d0-b)*p(i,i2)
     .            +(1d0-c)*p(i,i3)+(1d0-d)*p(i,i4)
        ppar(i,j3)=p(i,i5)
        p3(i,1) = ppar(i,j1)
        p3(i,2) = ppar(i,j2)
        p3(i,3) = ppar(i,j3)
      enddo

      ysum=y12+y14+y24
      y12=y12/ysum
      y14=y14/ysum
      y24=y24/ysum
      
       s(j2,j1)=s(j1,j2)
       s(j3,j1)=s(j1,j3)
       s(j3,j2)=s(j2,j3)
     
       s12=s(1,2)
       s13=s(1,3)
       s23=s(2,3)
    
      return
      end
*
************************************************************************
* definitions of li's in pmapK,C,D unified: always
* l1=a1*pi1+b1*pi2+c1*pi3, 
* l3=(1-a1)*pi1+(1-b1)*pi2+(1-c1)*pi3,
* l2=i4, 
* l4=i5
************************************************************************
* changed such that i3 is shared hard radiator 
* mapping where i3 is shared hard radiator (k in (2.24))
* first i2 unresolved, then i4 unresolved
      subroutine pmap5to4to3K(i1,i2,i3,i4,i5,j1,j2,j3)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      common /sa3/yij,yik,yjk
      common /sb3/wKm,wKl,wlm
      common /sc3/s12,s13,s23
      common /pmom/p(4,5) 
      common /tcuts/ymin,y0
      common /pcut/ppar(4,5) 

      common/mapmomenta/p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      dimension s(3,3)

      do i=1,4
         p5(i,1) = p(i,i1)
         p5(i,2) = p(i,i2)
         p5(i,3) = p(i,i3)
         p5(i,4) = p(i,i4)
         p5(i,5) = p(i,i5)
      enddo

      yij=y(i1,i2)
      yjk=y(i2,i3)
      yik=y(i1,i3)

*    i2 unresolved, i1,i3 radiators
      call DAK(yij,yjk,yik,a1,b1,c1)
      
*    l1=a1*pi1+b1*pi2+c1*pi3
*    l3=(1-a1)*pi1+(1-b1)*pi2+(1-c1)*pi3
*    l2=pi4 
*    l4=pi5      

      do i=1,4
         p4(i,1) = a1*p(i,i1) + b1*p(i,i2) + c1*p(i,i3)
         p4(i,3) = (1d0-a1)*p(i,i1) + (1d0-b1)*p(i,i2) 
     .            +(1d0-c1)*p(i,i3)
         p4(i,2) = p(i,i4)
         p4(i,4) = p(i,i5)
      enddo

      wKl=(1d0-a1)*y(i1,i4)+(1d0-b1)*y(i2,i4)+(1d0-c1)*y(i3,i4)
      wlm=y(i4,i5)      
      wKm=(1d0-a1)*y(i1,i5)+(1d0-b1)*y(i2,i5)+(1d0-c1)*y(i3,i5)        

*    l2=i4=l unresolved
*    l3=   K hard radiator
*    l4=i5=m hard radiator
*    l1      untouched

*     wKl=wl2l3,wlm=wl2l4,wKm=wl3l4
*
      call DAK(wKl,wlm,wKm,a2,b2,c2)
      
       c12 = -2d0*(-1d0 + a1)*(-1d0 + a2)*a2*(-1d0 + b1)
       c13 = -2d0*(-1d0 + a1)*(-1d0 + a2)*a2*(-1d0 + c1)
       c14 = (-1d0 + a1)*(-b2 + a2*(-1d0 + 2d0*b2))
       c15 = (-1d0 + a1)*(-c2 + a2*(-1d0 + 2d0*c2))
       c23 = -2d0*(-1d0 + a2)*a2*(-1d0 + b1)*(-1d0 + c1)
      c24 = (-1d0 + b1)*(-b2 + a2*(-1d0 + 2d0*b2))
      c25 = (-1d0 + b1)*(-c2 + a2*(-1d0 + 2d0*c2))
      c34 = (-b2 + a2*(-1d0 + 2d0*b2))*(-1d0 + c1)
      c35 = (-1d0 + c1)*(-c2 + a2*(-1d0 + 2d0*c2))
      c45 = b2 + c2 - 2d0*b2*c2
      d12 = a2*(a1 + b1 - 2d0*a1*b1)
      d13 = a2*(a1 + c1 - 2d0*a1*c1)
      d14 = a1*b2
      d15 = a1*c2
      d23 = a2*(b1 + c1 - 2d0*b1*c1)
      d24 = b1*b2
      d25 = b1*c2
      d34 = b2*c1
      d35 = c1*c2
      d45 = 0d0
      e12 = (-1d0 + a2)*(-b1 + a1*(-1d0 + 2d0*b1))
      e13 = (-1d0 + a2)*(-c1 + a1*(-1d0 + 2d0*c1))
      e14 = a1 - a1*b2
      e15 = a1 - a1*c2
      e23 = (-1d0 + a2)*(-c1 + b1*(-1d0 + 2d0*c1))
      e24 = b1 - b1*b2
      e25 = b1 - b1*c2
      e34 = c1 - b2*c1
      e35 = c1 - c1*c2
      e45 = 0d0
    
      s(j1,j2)=c12*y(i1,i2)+c13*y(i1,i3)+c14*y(i1,i4)+c15*y(i1,i5)
     .     +c23*y(i2,i3)+c24*y(i2,i4)+c25*y(i2,i5)
     .     +c34*y(i3,i4)+c35*y(i3,i5)+c45*y(i4,i5)        
      s(j1,j3)=d12*y(i1,i2)+d13*y(i1,i3)+d14*y(i1,i4)+d15*y(i1,i5)
     .     +d23*y(i2,i3)+d24*y(i2,i4)+d25*y(i2,i5)
     .     +d34*y(i3,i4)+d35*y(i3,i5)+d45*y(i4,i5)   
      s(j2,j3)=e12*y(i1,i2)+e13*y(i1,i3)+e14*y(i1,i4)+e15*y(i1,i5)
     .     +e23*y(i2,i3)+e24*y(i2,i4)+e25*y(i2,i5)
     .     +e34*y(i3,i4)+e35*y(i3,i5)+e45*y(i4,i5) 
      
       s(j2,j1)=s(j1,j2)
       s(j3,j1)=s(j1,j3)
       s(j3,j2)=s(j2,j3)

      do i=1,4
        ppar(i,j1)=a2*( (1d0-a1)*p(i,i1)+(1d0-b1)*p(i,i2)+
     #          	(1d0-c1)*p(i,i3) )
     #	          +b2*p(i,i4)+c2*p(i,i5)
        ppar(i,j2)=(1d0-a2)*((1d0-a1)*p(i,i1)+(1d0-b1)*p(i,i2)+
     #	                     (1d0-c1)*p(i,i3))
     #	          +(1d0-b2)*p(i,i4)+(1d0-c2)*p(i,i5)
	ppar(i,j3)=a1*p(i,i1)+b1*p(i,i2)+c1*p(i,i3)
        p3(i,1) = ppar(i,j1)
        p3(i,2) = ppar(i,j2)
        p3(i,3) = ppar(i,j3)
      enddo

       s12=s(1,2)
       s13=s(1,3)
       s23=s(2,3)

      ysum=yij+yjk+yik
      yij=yij/ysum
      yjk=yjk/ysum
      yik=yik/ysum
      
      return
      end
c   *****************************************************************
* needed if a COMBINED momentum (l3) becomes unresolved in second step
* i at position 5 remains untouched
* (e.g. for B50cds (NF/N sig3ds))
      subroutine pmap5to4to3C(i1,i2,i3,i4,i5,j1,j2,j3)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      common /sa3/y12,y13,y23
      common /sb3/wl1l2,wl1l3,wl2l3
      common /sc3/s12,s13,s23
      common /pmom/p(4,5) 
      common /pcut/ppar(4,5) 
      common/mapmomenta/p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      dimension s(3,3)

      do i=1,4
         p5(i,1) = p(i,i1)
         p5(i,2) = p(i,i2)
         p5(i,3) = p(i,i3)
         p5(i,4) = p(i,i4)
         p5(i,5) = p(i,i5)
      enddo

      y12=y(i1,i2)
      y13=y(i1,i3)
      y23=y(i2,i3)
      y34=y(i3,i4)

* first i2 unresolved, i1,i3 radiators
* yields combined momenta l1 and l3

      call DAK(y12,y23,y13,a1,b1,c1)

      wl1l3=         y(i1,i2)         +y(i1,i3)         +y(i2,i3)
      wl1l2=      a1*y(i1,i4)      +b1*y(i2,i4)      +c1*y(i3,i4)
      wl2l3=(1d0-a1)*y(i1,i4)+(1d0-b1)*y(i2,i4)+(1d0-c1)*y(i3,i4)
          
*     l1=a1*pi1+b1*pi2+c1*pi3
*     l3=(1-a1)*pi1+(1-b1)*pi2+(1-c1)*pi3
*     l2=pi4
*     l4=pi5

      do i=1,4
         p4(i,1) = a1*p(i,i1) + b1*p(i,i2) + c1*p(i,i3)
         p4(i,3) = (1d0-a1)*p(i,i1) + (1d0-b1)*p(i,i2) 
     .            +(1d0-c1)*p(i,i3)
         p4(i,2) = p(i,i4)
         p4(i,4) = p(i,i5)
      enddo



*  now l3 unresolved, l1,l2 radiators, l4 untouched
*  yields j1,j2,j3 with j3=l4=i5

      call DAK(wl1l3,wl2l3,wl1l2,a2,b2,c2)
      
      a=a2*a1+b2*(1d0-a1)
      b=a2*b1+b2*(1d0-b1)
      c=a2*c1+b2*(1d0-c1)
      d=c2
      
*      j1=a2*l1+b2*l3+c2*l2=a*pi1+b*pi2+c*pi3+d*pi4
*      j2=(1-a2)*l1+(1-b2)*l3+(1-c2)*l2=
*        (1-a)*pi1+(1-b)*pi2+(1-c)*pi3+(1-d)*pi4
*      j3=l4=pi5
*

c      (1-a2)*l1 = (1-a2)*(a1*pi1+b1*pi2+c1*pi3)
c      (1-b2)*l3 = (1-b2)*((1-a1)*pi1+(1-b1)*pi2+(1-c1)*pi3)
c      (1-c2)*l2 = (1-c2)*pi4

c sum:  =  pi1*(a1-a1*a2+1-b2-a1+a1*b2)   = 1-b2+a1*b2-a1*a2
c        + pi2*(b1-b1*a2+1-b2-b1+b1*b2)   = 1-b2+b1*b2-b1*a2
c        + pi3*(c1-c1*a2+1-b2-c1+c1*b2)   = 1-b2+c1*b2-c1*a2
c        + pi4*(1-c2)

      s(j1,j3)=   a*y(i1,i5)         +b*y(i2,i5)   
     .           +c*y(i3,i5)         +d*y(i4,i5)
      s(j2,j3)=(1d0-a)*y(i1,i5)   +(1d0-b)*y(i2,i5)    
     .        +(1d0-c)*y(i3,i5)   +(1d0-d)*y(i4,i5)
      s(j1,j2)= y(i1,i2)+y(i1,i3)+y(i1,i4)+y(i2,i3)+y(i2,i4)+y(i3,i4)
      
      s(j2,j1)=s(j1,j2)
      s(j3,j1)=s(j1,j3)
      s(j3,j2)=s(j2,j3)

      do i=1,4
        ppar(i,j1)=      a*p(i,i1)      +b*p(i,i2)
     .          	+c*p(i,i3)      +d*p(i,i4)
        ppar(i,j2)=(1d0-a)*p(i,i1)+(1d0-b)*p(i,i2)
     .            +(1d0-c)*p(i,i3)+(1d0-d)*p(i,i4)
        ppar(i,j3)=p(i,i5)
        p3(i,1) = ppar(i,j1)
        p3(i,2) = ppar(i,j2)
        p3(i,3) = ppar(i,j3)
      enddo

      ysum=y12+y13+y23
      y12=y12/ysum
      y13=y13/ysum
      y23=y23/ysum
      
      wsum=wl1l3+wl1l2+wl2l3
      
       s12=s(1,2)
       s13=s(1,3)
       s23=s(2,3)
      
      return
      end
*
************************************************************************
* needed if first combined momentum (l1) becomes unresolved in second step
* i at position 5 remains untouched
* (e.g. for B50dds (NF/N sig3ds))
* corresponds to pmap5to4to3C with l1<->l3
* order in common/sb3/ changed such that first entry contains the
* two radiators 
      subroutine pmap5to4to3D(i1,i2,i3,i4,i5,j1,j2,j3)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      common /sa3/y12,y13,y23
      common /sb3/wl2l3,wl1l2,wl1l3
      common /sc3/s12,s13,s23
      common /pmom/p(4,5) 
      common /pcut/ppar(4,5) 
      common/mapmomenta/p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      dimension s(3,3)

      do i=1,4
         p5(i,1) = p(i,i1)
         p5(i,2) = p(i,i2)
         p5(i,3) = p(i,i3)
         p5(i,4) = p(i,i4)
         p5(i,5) = p(i,i5)
      enddo

      y12=y(i1,i2)
      y13=y(i1,i3)
      y23=y(i2,i3)

* first i2 unresolved, i1,i3 radiators

      call DAK(y12,y23,y13,a1,b1,c1)

      wl1l3=         y(i1,i2)         +y(i1,i3)         +y(i2,i3)
      wl1l2=      a1*y(i1,i4)      +b1*y(i2,i4)      +c1*y(i3,i4)
      wl2l3=(1d0-a1)*y(i1,i4)+(1d0-b1)*y(i2,i4)+(1d0-c1)*y(i3,i4)
          
*     l1=a1*pi1+b1*pi2+c1*pi3
*     l3=(1-a1)*pi1+(1-b1)*pi2+(1-c1)*pi3
*     l2=pi4
*     l4=pi5

      do i=1,4
         p4(i,1) = a1*p(i,i1) + b1*p(i,i2) + c1*p(i,i3)
         p4(i,3) = (1d0-a1)*p(i,i1) + (1d0-b1)*p(i,i2) 
     .            +(1d0-c1)*p(i,i3)
         p4(i,2) = p(i,i4)
         p4(i,4) = p(i,i5)
      enddo
*  now l1 unresolved, l2,l3 radiators (l2=i4), l4=i5 untouched

      call DAK(wl1l2,wl1l3,wl2l3,a2,b2,c2)
      
      a=b2*a1+c2*(1d0-a1)
      b=b2*b1+c2*(1d0-b1)
      c=b2*c1+c2*(1d0-c1)
      d=a2
      
*      j1=a2*l2+b2*l1+c2*l3=a*pi1+b*pi2+c*pi3+d*pi4
*      j2=(1-a2)*l2+(1-b2)*l1+(1-c2)*l3=
*        (1-a)*pi1+(1-b)*pi2+(1-c)*pi3+(1-d)*pi4
*      j3=l4=pi5
*
      
      s(j1,j3)=      a*y(i1,i5)         +b*y(i2,i5)   
     .              +c*y(i3,i5)         +d*y(i4,i5)
      s(j2,j3)=(1d0-a)*y(i1,i5)   +(1d0-b)*y(i2,i5)    
     .        +(1d0-c)*y(i3,i5)   +(1d0-d)*y(i4,i5)
      s(j1,j2)= y(i1,i2)+y(i1,i3)+y(i1,i4)+y(i2,i3)+y(i2,i4)+y(i3,i4)
      
      s(j2,j1)=s(j1,j2)
      s(j3,j1)=s(j1,j3)
      s(j3,j2)=s(j2,j3)

      do i=1,4
        ppar(i,j1)=      a*p(i,i1)      +b*p(i,i2)
     .          	+c*p(i,i3)      +d*p(i,i4)
        ppar(i,j2)=(1d0-a)*p(i,i1)+(1d0-b)*p(i,i2)
     .            +(1d0-c)*p(i,i3)+(1d0-d)*p(i,i4)
        ppar(i,j3)=p(i,i5)
        p3(i,1) = ppar(i,j1)
        p3(i,2) = ppar(i,j2)
        p3(i,3) = ppar(i,j3)
      enddo

      s12=s(1,2)
      s13=s(1,3)
      s23=s(2,3)

      ysum=y12+y13+y23
      y12=y12/ysum
      y13=y13/ysum
      y23=y23/ysum
            
      return
      end
*
************************************************************************
*************************************************************************
* five parton double unresolved subtraction terms
c -------------------------------------------------------------------
c
      function A345dsA40t(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      common /s3/s12,s13,s23
      common /sa3/u12,u13,u23
      common /sb3/w12,w13,w23
      common /sc3/x12,x13,x23
      common /plots/plot
      logical plot 

      wt=0d0
*
* (o,p,q), analogous to 1/N^2 (A345qds) with j->k
* note:
* A40tilde(i1,i3,i4,i2)=(Aqppq(i1,i3,i4,i2)+Aqppq(i1,i4,i3,i2))/4d0 
* sum only over permutations 345 and 543 as this is the way
* the 5-parton ME is included
* overall factor 4 relative to (5.3) as usual to cancel with 
* 1/4 in overall cflo*(as/2d0/pi)**3/4d0 in sig3ds
*
       fac=1d0
*
* (o): (i,k)=(3,5)
      call pmap5to3(i1,i3,i5,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -Aqppq(i1,i3,i5,i2)*
     #	   A30y5map(s12,s13,s23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* (o): (i,k)=(5,3)
*
      call pmap5to3(i1,i5,i3,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -Aqppq(i1,i5,i3,i2)*
     #	   A30y5map(s12,s13,s23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*	
* (p): (i,k)=(3,5)
*
      call pmap5to4to3(i1,i3,i5,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = 4d0*A30y5(i1,i3,i2)*A30y5map(w12,w13,w23)
     .                    *A30y5map(x12,x13,x23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* (q): (p) with 3<->5 
*
      call pmap5to4to3(i1,i5,i3,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = 4d0*A30y5(i1,i5,i2)*A30y5map(w12,w13,w23)
     .                    *A30y5map(x12,x13,x23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
	
      A345dsA40t = wt
 
      return
      end

************************************************************************
c
      function A345dsD40(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      common /s3/s12,s13,s23
      common /s4/r12,r13,r14,r23,r24,r34
      common /sa3/u12,u13,u23
      common /sb3/w12,w13,w23
      common /sc3/x12,x13,x23
      common /plots/plot
      logical plot 

      wt=0d0
* factor 4 overall factor, NOT divided by 3! as in (5.3) 
* because cyclic permus are not included in ME nor below
* note that sig3ds contains 1/4*1/6*6 in N^2 part  
      fac=4d0

      y12=y(i1,i2)
      y13=y(i1,i3)
      y14=y(i1,i4)
      y15=y(i1,i5)
      y23=y(i2,i3)
      y24=y(i2,i4)
      y25=y(i2,i5)
      y34=y(i3,i4)
      y35=y(i3,i5)
      y45=y(i4,i5)



* (g): (i,j,k)=(3,4,5)
      D40 = D40i(i1,i3,i4,i5)
      Da  = D40a(i1,i3,i4,i5)
      Db  = D40a(i1,i5,i4,i3)
      Dc  = D40c(i1,i3,i4,i5)
      Dd  = D40c(i1,i5,i4,i3)
      Dleft = D40 -(Da+Db+Dc+Dd)
      Da  = Da + Dleft/2d0
      Db  = Db + Dleft/2d0


*** Mapping A: (1345)
      call pmap5to3(i1,i3,i4,i5,i2,1,3,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = Da*
     #	   A30y5map(s12,s13,s23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif

*** Mapping B: (1543)
      call pmap5to3(i1,i5,i4,i3,i2,1,3,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = Db*
     #	   A30y5map(s12,s13,s23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif

*** Mapping C: (1354)
      call pmap5to3(i1,i3,i5,i4,i2,1,3,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = Dc*
     #	   A30y5map(s12,s13,s23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif

*** Mapping D: (1354)
      call pmap5to3(i1,i5,i3,i4,i2,1,3,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = Dd*
     #	   A30y5map(s12,s13,s23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
********************************************************************
*  (h): (i,j,k)=(3,4,5)
* split into  (1) (i3i4tilde) unresolved in second step,
*             (2) i5 unresolved in second step,
*
      call pmap5to4to3C(i1,i3,i4,i5,i2,1,3,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -sd30y5(i1,i3,i4)*
     .       sd30y5map(w12,w13,w23)*A30y5map(x12,x13,x23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*	
      call pmap5to4to3(i1,i3,i5,i4,i2,1,3,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -sd30y5(i1,i3,i4)*
     .       sd30y5map(w12,w13,w23)*A30y5map(x12,x13,x23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
*  (i): (i,j,k)=(3,4,5)
* split into  (1) (i4i5tilde) unresolved in second step
*             (2) (i3i4tilde) unresolved in second step
*
      call pmap5to4to3C(i3,i4,i5,i1,i2,3,1,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -sf30y5(i3,i4,i5)*
     .       sd30y5map(w12,w23,w13)*A30y5map(x12,x13,x23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
      call pmap5to4to3D(i3,i4,i5,i1,i2,1,3,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -sf30y5(i3,i4,i5)*
     .       sd30y5map(w12,w13,w23)*A30y5map(x12,x13,x23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
*  (j): (h) with 3<->5 
*
      call pmap5to4to3C(i1,i5,i4,i3,i2,1,3,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -sd30y5(i1,i5,i4)*
     .       sd30y5map(w12,w13,w23)*A30y5map(x12,x13,x23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*	
      call pmap5to4to3(i1,i5,i3,i4,i2,1,3,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -sd30y5(i1,i5,i4)*
     .       sd30y5map(w12,w13,w23)*A30y5map(x12,x13,x23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
************************************************************
* (k,l,m,n): interchange 1<->2 in (g,h,i,j)
*
* (k): (i,j,k)=(3,4,5)

      D40 = D40i(i2,i3,i4,i5)
      Da  = D40a(i2,i3,i4,i5)
      Db  = D40a(i2,i5,i4,i3)
      Dc  = D40c(i2,i3,i4,i5)
      Dd  = D40c(i2,i5,i4,i3)
      Dleft = D40 -(Da+Db+Dc+Dd)
      Da  = Da + Dleft/2d0
      Db  = Db + Dleft/2d0
*** Mapping A: (2345)

      call pmap5to3(i2,i3,i4,i5,i1,2,3,1)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = Da*
     #	   A30y5map(s12,s13,s23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif

*** Mapping B: (2543)
      call pmap5to3(i2,i5,i4,i3,i1,2,3,1)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = Db*
     #	   A30y5map(s12,s13,s23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif

*** Mapping C: (2354)
      call pmap5to3(i2,i3,i5,i4,i1,2,3,1)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = Dc*
     #	   A30y5map(s12,s13,s23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif

*** Mapping D: (2534)
      call pmap5to3(i2,i5,i3,i4,i1,2,3,1)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = Dd*
     #	   A30y5map(s12,s13,s23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif

*
*  (l): (i,j,k)=(3,4,5)
*
      call pmap5to4to3C(i2,i3,i4,i5,i1,2,3,1)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -sd30y5(i2,i3,i4)*
     .       sd30y5map(w12,w13,w23)*A30y5map(x12,x13,x23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*	
      call pmap5to4to3(i2,i3,i5,i4,i1,2,3,1)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -sd30y5(i2,i3,i4)*
     .       sd30y5map(w12,w13,w23)*A30y5map(x12,x13,x23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
*  (m): (i,j,k)=(3,4,5)
*
      call pmap5to4to3C(i3,i4,i5,i2,i1,3,2,1)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -sf30y5(i3,i4,i5)*
     .       sd30y5map(w12,w23,w13)*A30y5map(x12,x13,x23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
      call pmap5to4to3D(i3,i4,i5,i2,i1,2,3,1)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -sf30y5(i3,i4,i5)*
     .       sd30y5map(w12,w13,w23)*A30y5map(x12,x13,x23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
*  (n): (l) with 3<->5
*
      call pmap5to4to3(i2,i5,i3,i4,i1,2,3,1)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -sd30y5(i2,i5,i4)*
     .       sd30y5map(w12,w13,w23)*A30y5map(x12,x13,x23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*	
      call pmap5to4to3C(i2,i5,i4,i3,i1,2,3,1)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -sd30y5(i2,i5,i4)*
     .       sd30y5map(w12,w13,w23)*A30y5map(x12,x13,x23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
******************************************************************
* 
* (r): (i,j,k)=(3,4,5) 
*
      call pmap5to4to3K(i1,i3,i4,i5,i2,3,2,1)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -sd30y5(i1,i3,i4)*sd30y5map(w12,w23,w13)
     .                 *A30y5map(x12,x13,x23)*var*fac/2d0
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* (s): (r) with 1<->2 and 3<->5
*
      call pmap5to4to3K(i2,i5,i4,i3,i1,3,1,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -sd30y5(i2,i5,i4)*sd30y5map(w12,w23,w13)
     .                 *A30y5map(x12,x13,x23)*var*fac/2d0
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* (t): (s) with 1<->2 
*
      call pmap5to4to3K(i1,i5,i4,i3,i2,3,2,1)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -sd30y5(i1,i5,i4)*sd30y5map(w12,w23,w13)
     .                 *A30y5map(x12,x13,x23)*var*fac/2d0
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* (u): (r) with 1<->2 
*
      call pmap5to4to3K(i2,i3,i4,i5,i1,3,1,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -sd30y5(i2,i3,i4)*sd30y5map(w12,w23,w13)
     .                 *A30y5map(x12,x13,x23)*var*fac/2d0
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
******************************************************************	
* (v): 
*
      call pmap5to4to3(i1,i3,i5,i4,i2,1,3,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = sd30y5(i1,i3,i4)*sd30y5map(w12,w13,w23)
     .                 *A30y5map(x12,x13,x23)*var*fac/2d0
           wtsoft =  ( (sant(21,2,22)-sant(11,2,13))
     .                -(sant(23,2,22)-sant(23,2,13))
     .                -(sant(21,2,23)-sant(11,2,23)))
     .                *sd30y5map(w12,w13,w23)
     .                 *A30y5map(x12,x13,x23)*var*fac/2d0
           wtsub = wtsub + wtsoft
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*	
* (w): (v) with 3<->5
*
      call pmap5to4to3(i1,i5,i3,i4,i2,1,3,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = sd30y5(i1,i5,i4)*sd30y5map(w12,w13,w23)
     .                 *A30y5map(x12,x13,x23)*var*fac/2d0
           wtsoft =  ( (sant(21,2,22)-sant(11,2,13))
     .                -(sant(23,2,22)-sant(23,2,13))
     .                -(sant(21,2,23)-sant(11,2,23)))
     .                *sd30y5map(w12,w13,w23)
     .                 *A30y5map(x12,x13,x23)*var*fac/2d0
           wtsub = wtsub + wtsoft
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* (x): (v) with 1<->2
*
      call pmap5to4to3(i2,i3,i5,i4,i1,2,3,1)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = sd30y5(i2,i3,i4)*sd30y5map(w12,w13,w23)
     .                 *A30y5map(x12,x13,x23)*var*fac/2d0
           wtsoft =  ( (sant(21,2,22)-sant(11,2,13))
     .                -(sant(23,2,22)-sant(23,2,13))
     .                -(sant(21,2,23)-sant(11,2,23)))
     .                *sd30y5map(w12,w13,w23)
     .                 *A30y5map(x12,x13,x23)*var*fac/2d0
           wtsub = wtsub + wtsoft
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*	
* (y): (x) with 3<->5	
*
      call pmap5to4to3(i2,i5,i3,i4,i1,2,3,1)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = sd30y5(i2,i5,i4)*sd30y5map(w12,w13,w23)
     .                 *A30y5map(x12,x13,x23)*var*fac/2d0
           wtsoft =  ( (sant(21,2,22)-sant(11,2,13))
     .                -(sant(23,2,22)-sant(23,2,13))
     .                -(sant(21,2,23)-sant(11,2,23)))
     .                *sd30y5map(w12,w13,w23)
     .                 *A30y5map(x12,x13,x23)*var*fac/2d0
           wtsub = wtsub + wtsoft
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*********************************************************************
* 
* (aa)
*
      call pmap5to4to3K(i2,i3,i1,i5,i4,1,3,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -A30y5(i1,i3,i2)*sd30y5map(w12,w13,w23)
     .                 *A30y5map(x12,x13,x23)*var*fac/2d0
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* (ab): 
*
      call pmap5to4to3K(i4,i5,i1,i3,i2,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = sd30y5(i1,i5,i4)*A30y5map(w12,w13,w23)
     .                 *A30y5map(x12,x13,x23)*var*fac/2d0
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*		
* (ac): (aa) with 3<->5
*
      call pmap5to4to3K(i2,i5,i1,i3,i4,1,3,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -A30y5(i1,i5,i2)*sd30y5map(w12,w13,w23)
     .                 *A30y5map(x12,x13,x23)*var*fac/2d0
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* (ad): (ab) with 3<->5
*
      call pmap5to4to3K(i4,i3,i1,i5,i2,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = sd30y5(i1,i3,i4)*A30y5map(w12,w13,w23)
     .                 *A30y5map(x12,x13,x23)*var*fac/2d0
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*			
* (ae): (aa) with 1<->2
*
      call pmap5to4to3K(i1,i3,i2,i5,i4,2,3,1)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -A30y5(i2,i3,i1)*sd30y5map(w12,w13,w23)
     .                 *A30y5map(x12,x13,x23)*var*fac/2d0
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* (af): (ab) with 1<->2
*
      call pmap5to4to3K(i4,i5,i2,i3,i1,2,1,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = sd30y5(i2,i5,i4)*A30y5map(w12,w13,w23)
     .                 *A30y5map(x12,x13,x23)*var*fac/2d0
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* (ag): (ac) with 1<->2
*      
      call pmap5to4to3K(i1,i5,i2,i3,i4,2,3,1)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -A30y5(i2,i5,i1)*sd30y5map(w12,w13,w23)
     .                 *A30y5map(x12,x13,x23)*var*fac/2d0
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*	
* (ah): (ad) with 1<->2	
*
      call pmap5to4to3K(i4,i3,i2,i5,i1,2,1,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = sd30y5(i2,i3,i4)*A30y5map(w12,w13,w23)
     .                 *A30y5map(x12,x13,x23)*var*fac/2d0
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*	
* (ai): 1-5-3-2 antenna
      call pmap5to4to3(i1,i5,i3,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -A30y5(i1,i5,i2)*
     .       A30y5map(w12,w13,w23)*A30y5map(x12,x13,x23)*var*fac/2d0
           wtsoft = -( (sant(21,2,22)-sant(11,2,13))
     .                -(sant(23,2,22)-sant(23,2,13))
     .                -(sant(21,2,23)-sant(11,2,23)))
     .                *A30y5map(w12,w13,w23)
     .                 *A30y5map(x12,x13,x23)*var*fac/2d0
           wtsub = wtsub + wtsoft
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* (aj): (ai) with 5<->3
      call pmap5to4to3(i1,i3,i5,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -A30y5(i1,i3,i2)*
     .       A30y5map(w12,w13,w23)*A30y5map(x12,x13,x23)*var*fac/2d0
           wtsoft = -( (sant(21,2,22)-sant(11,2,13))
     .                -(sant(23,2,22)-sant(23,2,13))
     .                -(sant(21,2,23)-sant(11,2,23)))
     .                *A30y5map(w12,w13,w23)
     .                 *A30y5map(x12,x13,x23)*var*fac/2d0
           wtsub = wtsub + wtsoft
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif

      A345dsD40 = wt

      return
      end

*********************************************************************
c 21.7.06  for N^0:
*********************************************************************
      function AN0a(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      common /s3/s12,s13,s23
      common /sa3/u12,u13,u23
      common /sb3/w12,w13,w23
      common /sc3/x12,x13,x23
      common /plots/plot
      logical plot 

      wt=0d0
*
* factor 4 cancels 1/4 from overall cflo*(as/2d0/pi)**3/4d0
* in sig3ds, other factors as well as sum over (3,4) 
* are included in sig111.f already
*
      fac=4d0
*
* 1-3-4-2 antenna
* 
* (g):
      call pmap5to3(i1,i3,i4,i2,i5,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = A40i(i1,i3,i4,i2)*
     #	   A30y5map(s12,s13,s23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* (h): 
      call pmap5to4to3C(i1,i3,i4,i2,i5,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -sd30y5(i1,i3,i4)*
     #       A30y5map(w12,w13,w23)*
     #       A30y5map(x12,x13,x23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*	
* (i): exchange 1 <-> 2 
*
      call pmap5to4to3C(i2,i4,i3,i1,i5,2,1,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -sd30y5(i2,i4,i3)*
     #       A30y5map(w12,w23,w13)*
     #       A30y5map(x12,x13,x23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*	
      AN0a = wt

      return
      end

************************************************************************
*
      function AN0b(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      common /s3/s12,s13,s23
      common /sa3/u12,u13,u23
      common /sb3/w12,w13,w23
      common /sc3/x12,x13,x23
      common /plots/plot
      logical plot 

      wt=0d0
*
* note:
* A40tilde(i1,i3,i4,i2)=(Aqppq(i1,i3,i4,i2)+Aqppq(i1,i4,i3,i2))/4d0 
* overall factor 4 relative to (6.2) as usual
* factor -1/3 is already included in sig111.f
*
       fac=1d0
*
*
* 1-3-5-2 antenna
*
* term (j) in (6.2):
*
      call pmap5to3(i1,i3,i5,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = Aqppq(i1,i3,i5,i2)*
     #	   A30y5map(s12,s13,s23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*	
* account for fact that i<->j needs to be added to construct A40tilde 
* from Aqppq
*
* 1-5-3-2 antenna
*
      call pmap5to3(i1,i5,i3,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = Aqppq(i1,i5,i3,i2)*
     #	   A30y5map(s12,s13,s23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*	
* 1-3-5-2 antenna
* term (k) in (6.2):
      call pmap5to4to3(i1,i3,i5,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -4d0*A30y5(i1,i3,i2)*A30y5map(w12,w13,w23)
     .            *A30y5map(x12,x13,x23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* 1-5-3-2 antenna
* term (l)
      call pmap5to4to3(i1,i5,i3,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -4d0*A30y5(i1,i5,i2)*A30y5map(w12,w13,w23)
     .            *A30y5map(x12,x13,x23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
	
      AN0b = wt
 
      return
      end

***********************************************************************
      function AN0c(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      common /s3/s12,s13,s23
      common /sa3/u12,u13,u23
      common /sb3/w12,w13,w23
      common /sc3/x12,x13,x23
      common /checkplot/ic
      common /plots/plot
      logical plot 
      
      wt=0d0
c overall factor 1/2 and sum over 3<->4 are  included in sig111.f      
      fac=1d0
      if (ic.eq.1) write(6,*) i1,i2,i3,i4,i5
*
* term (q) in (6.2)
      call pmap5to4to3K(i4,i3,i1,i5,i2,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
         wtsub = sd30y5(i1,i3,i4)*A30y5map(w12,w13,w23)*
     #                 A30y5map(x12,x13,x23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* term (r): (q) with 1<->2 
      call pmap5to4to3K(i4,i3,i2,i5,i1,2,1,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = sd30y5(i2,i3,i4)*A30y5map(w12,w23,w13)
     #             *A30y5map(x12,x13,x23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*  
* term (s):    
      call pmap5to4to3(i1,i3,i5,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -A30y5(i1,i3,i2)*
     #       A30y5map(w12,w13,w23)*
     #       A30y5map(x12,x13,x23)*var*fac
           wtsoft = (-(sant(21,2,22)-sant(11,2,13))
     .               +(sant(21,2,23)-sant(11,2,23))
     .               +(sant(22,2,23)-sant(13,2,23)))
     .                 *A30y5map(w12,w13,w23)
     .                 *A30y5map(x12,x13,x23)*var*fac
           if (ic.eq.1) write(6,*) 's',wtsub,wtsoft,wtsub+wtsoft
           wtsub = wtsub + wtsoft
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
 
      AN0c = wt

      return
      end
***********************************************************************
c A34Qds is like A345qds of 1/N^2, but no sum over (345) permutations
c
      function A34Qds(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      common /s3/s12,s13,s23
      common /sa3/u12,u13,u23
      common /sb3/w12,w13,w23
      common /sc3/x12,x13,x23
      common /plots/plot
      logical plot 

      wt=0d0
c factor 1/6 is included in signew.f already      
* note:
* A40tilde(i1,i3,i4,i2)=(Aqppq(i1,i3,i4,i2)+Aqppq(i1,i4,i3,i2))/4d0
* such that overall factor 4 relative to (6.2) is included implicitly 
* factor 4 relative to (6.2) is "removed" in sig3ds by overall
* factor cflo*(as/2d0/pi)**3/4d0 
*
      fac=1d0
*
* 1-3-4-2 antenna
* (m) in (6.2)
      call pmap5to3(i1,i3,i4,i2,i5,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = Aqppq(i1,i3,i4,i2)*
     #	   A30y5map(s12,s13,s23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* 1-4-3-2 antenna
* (m) in (6.2)
      call pmap5to3(i1,i4,i3,i2,i5,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = Aqppq(i1,i4,i3,i2)*
     #	   A30y5map(s12,s13,s23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* 1-3-4-2 antenna
* (n) in (6.2)
      call pmap5to4to3(i1,i3,i4,i2,i5,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -4d0*A30y5(i1,i3,i2)*
     #       A30y5map(w12,w13,w23)*
     #       A30y5map(x12,x13,x23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* 1-4-3-2 antenna
* (o) in (6.2)
      call pmap5to4to3(i1,i4,i3,i2,i5,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -4d0*A30y5(i1,i4,i2)*A30y5map(w12,w13,w23)
     .                 *A30y5map(x12,x13,x23)*var*fac
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*	
      A34Qds = wt

      return
      end

***********************************************************************
* for 1/N^2
      function A345qds(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      common /s3/s12,s13,s23
      common /sa3/u12,u13,u23
      common /sb3/w12,w13,w23
      common /sc3/x12,x13,x23
      common /plots/plot
      logical plot 

      wt=0d0
*
* 1-3-4-2 antenna
*
      call pmap5to3(i1,i3,i4,i2,i5,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = Aqppq(i1,i3,i4,i2)*
     #	   A30y5map(s12,s13,s23)*var
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* 1-4-3-2 antenna
*
      call pmap5to3(i1,i4,i3,i2,i5,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = Aqppq(i1,i4,i3,i2)*
     #	   A30y5map(s12,s13,s23)*var
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* 1-3-5-2 antenna
*
      call pmap5to3(i1,i3,i5,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = Aqppq(i1,i3,i5,i2)*
     #	   A30y5map(s12,s13,s23)*var
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* 1-5-3-2 antenna
*
      call pmap5to3(i1,i5,i3,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = Aqppq(i1,i5,i3,i2)*
     #	   A30y5map(s12,s13,s23)*var
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* 1-4-5-2 antenna
*
      call pmap5to3(i1,i4,i5,i2,i3,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = Aqppq(i1,i4,i5,i2)*
     #	   A30y5map(s12,s13,s23)*var
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* 1-5-4-2 antenna
*
      call pmap5to3(i1,i5,i4,i2,i3,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = Aqppq(i1,i5,i4,i2)*
     #	   A30y5map(s12,s13,s23)*var
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* 1-3-4-2 antenna
*Aqgq=2*A30 => multiply with additional factor 2
      call pmap5to4to3(i1,i3,i4,i2,i5,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -4d0*A30y5(i1,i3,i2)*
     .       A30y5map(w12,w13,w23)*A30y5map(x12,x13,x23)*var
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* 1-4-3-2 antenna
*
      call pmap5to4to3(i1,i4,i3,i2,i5,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -4d0*A30y5(i1,i4,i2)*A30y5map(w12,w13,w23)
     .                 *A30y5map(x12,x13,x23)*var
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* 1-3-5-2 antenna
*
      call pmap5to4to3(i1,i3,i5,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -4d0*A30y5(i1,i3,i2)*A30y5map(w12,w13,w23)
     .                    *A30y5map(x12,x13,x23)*var
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* 1-5-3-2 antenna
*
      call pmap5to4to3(i1,i5,i3,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -4d0*A30y5(i1,i5,i2)*A30y5map(w12,w13,w23)
     .                    *A30y5map(x12,x13,x23)*var
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* 1-4-5-2 antenna
*
      call pmap5to4to3(i1,i4,i5,i2,i3,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -4d0*A30y5(i1,i4,i2)*A30y5map(w12,w13,w23)
     .                    *A30y5map(x12,x13,x23)*var
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* 1-5-4-2 antenna
*
      call pmap5to4to3(i1,i5,i4,i2,i3,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
           wtsub = -4d0*A30y5(i1,i5,i2)*A30y5map(w12,w13,w23)
     .                    *A30y5map(x12,x13,x23)*var
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
	
      A345qds = wt

      return
      end

************************************************************************
*
* Bfin = -2*C40*s1234, Aqgq=2*A30 
*
      function AAAAds(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      common /s3/s12,s13,s23
      common /plots/plot
      logical plot 
      
      y12=y(i1,i2)
      y13=y(i1,i3)
      y23=y(i2,i3)
      y14=y(i1,i4)
      y24=y(i2,i4)
      y34=y(i3,i4)
      y15=y(i1,i5)
      y25=y(i2,i5)
      y35=y(i3,i5)
      y45=y(i4,i5)

      wt=0d0
*
* 2-3-4 triple collinear  
*
      call pmap5to3(i1,i2,i3,i4,i5,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
      testA=y12+y13+y14+y23+y24+y34
       wtsub = -4d0*C40i(i1,i3,i4,i2)
     #         *A30y5map(s12,s13,s23)*var
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif

      AAAAds = wt

      return
      end

c -------------------------------------------------------------------
c corresponds to ??? (factor* small a40tilde) in (5.28)
c (9.69)
      function Aqppqold(i1,i3,i4,i2)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      y12=y(i1,i2)
      y13=y(i1,i3)
      y23=y(i2,i3)
      y14=y(i1,i4)
      y24=y(i2,i4)
      y34=y(i3,i4)
      y1234=y12+y13+y14+y23+y24+y34
      y12=y12/y1234
      y13=y13/y1234
      y14=y14/y1234
      y23=y23/y1234
      y24=y24/y1234
      y34=y34/y1234
      y134=y13+y14+y34
      y234=y23+y24+y34
      y13py23=y13+y23
      y14py24=y14+y24
      y13py14=y13+y14
      y23py24=y23+y24

      wt =
     &  + y13**(-1)*y24**(-1)*y13py23**(-1)*y14py24**(-1) * (  - 8*
     &    y12**3 )
      wt = wt + y13**(-1)*y24**(-1)*y13py23**(-1) * (  - 4*y12*
     &    y14 - 8*y12**2 )
      wt = wt + y13**(-1)*y24**(-1)*y14py24**(-1) * (  - 4*y12*
     &    y23 - 8*y12**2 )
      wt = wt + y13**(-1)*y24**(-1)*y134**(-1)*y234**(-1) * (  - 4*
     &    y12*y14*y23 - 8*y12*y23**2 - 16*y12**2*y23 - 8*y12**3 - 4*
     &    y14**2*y23 )
      wt = wt + y13**(-1)*y24**(-1)*y134**(-1) * (  - 4*y12*y23 - 4
     &    *y14*y23 - 4*y23**2 )
      wt = wt + y13**(-1)*y24**(-1)*y234**(-1) * (  - 12*y12*y14 - 
     &    8*y12*y23 - 16*y12**2 - 4*y14**2 )
      wt = wt + y13**(-1)*y24**(-1) * (  - 12*y12 - 8*y14 - 8*y23
     &     - 4*y34 )
      wt = wt + y13**(-1)*y13py23**(-1)*y14py24**(-1) * (  - 8*
     &    y12**3*y13py14**(-1) )
      wt = wt + y13**(-1)*y13py23**(-1)*y134**(-1)*y234**(-1)
     &  * (  - 8*y12**3 )
      wt = wt + y13**(-1)*y13py23**(-1)*y134**(-1) * ( 4*y12*y14
     &     - 4*y12*y24 - 8*y12**2 )
      wt = wt + y13**(-1)*y13py23**(-1)*y234**(-1) * (  - 4*y12*
     &    y14 + 4*y12*y24 - 8*y12**2 )
      wt = wt + y13**(-1)*y13py23**(-1) * (  - 4*y12*y24*
     &    y13py14**(-1) - 8*y12 - 8*y12**2*y13py14**(-1) )
      wt = wt + y13**(-1)*y14py24**(-1) * (  - 4*y12*y23*
     &    y13py14**(-1) - 8*y12**2*y13py14**(-1) )
      wt = wt + y13**(-1)*y134**(-2) * ( 4*y12*y14 + 4*y14*y23 + 4*
     &    y14*y24 )
      wt = wt + y13**(-1)*y134**(-1)*y234**(-1) * (  - 6*y12*y14 - 
     &    2*y12*y23 + 6*y12*y24 - 16*y12**2 + 6*y14*y23 + 6*y14*y24 - 4
     &    *y14**2 + 2*y23**2 - 2*y24**2 )
      wt = wt + y13**(-1)*y134**(-1) * (  - 10*y12 - 2*y23 + 2*y24
     &     )
      wt = wt + y13**(-1)*y234**(-1) * ( 6*y12 + 8*y14 + 2*y23 - 2*
     &    y24 )
      wt = wt + y13**(-1) * (  - 8*y12*y13py14**(-1) )
      wt = wt + y24**(-1)*y13py23**(-1)*y14py24**(-1) * (  - 8*
     &    y12**3*y23py24**(-1) )
      wt = wt + y24**(-1)*y13py23**(-1) * (  - 4*y12*y14*
     &    y23py24**(-1) - 8*y12**2*y23py24**(-1) )
      wt = wt + y24**(-1)*y14py24**(-1)*y134**(-1)*y234**(-1)
     &  * (  - 8*y12**3 )
      wt = wt + y24**(-1)*y14py24**(-1)*y134**(-1) * ( 4*y12*y13
     &     - 4*y12*y23 - 8*y12**2 )
      wt = wt + y24**(-1)*y14py24**(-1)*y234**(-1) * (  - 4*y12*
     &    y13 + 4*y12*y23 - 8*y12**2 )
      wt = wt + y24**(-1)*y14py24**(-1) * (  - 4*y12*y13*
     &    y23py24**(-1) - 8*y12 - 8*y12**2*y23py24**(-1) )
      wt = wt + y24**(-1)*y134**(-1)*y234**(-1) * ( 6*y12*y13 + 6*
     &    y12*y14 + 2*y12*y23 - 2*y13*y14 - 2*y13**2 - 2*y14*y23 + 2*
     &    y23**2 )
      wt = wt + y24**(-1)*y134**(-1) * ( 6*y12 - 2*y13 + 2*y23 )
      wt = wt + y24**(-1)*y234**(-2) * ( 4*y12*y23 + 4*y13*y23 + 4*
     &    y14*y23 )
      wt = wt + y24**(-1)*y234**(-1) * (  - 10*y12 + 2*y13 + 6*y23
     &     )
      wt = wt + y24**(-1) * (  - 8*y12*y23py24**(-1) )
      wt = wt + y134**(-1)*y234**(-1) * (  - 8*y12 + y13 - y14 + 
     &    y23 - y24 )
      wt = wt + y134**(-1) * ( 2 )
      wt = wt + y234**(-1) * ( 2 )

      Aqppqold=-2d0/y1234**2*wt/2d0

      return
      end

*
c -------------------------------------------------------------------
c corresponds to 4*(a40tilde(1342)+a40tilde(2431)) in (5.28)
c see Aqppq.m
c (9.69)
      function Aqppq(i1,i3,i4,i2)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      y12=y(i1,i2)
      y13=y(i1,i3)
      y23=y(i2,i3)
      y14=y(i1,i4)
      y24=y(i2,i4)
      y34=y(i3,i4)
      y1234=y12+y13+y14+y23+y24+y34
      y12=y12/y1234
      y13=y13/y1234
      y14=y14/y1234
      y23=y23/y1234
      y24=y24/y1234
      y34=y34/y1234
      y134=y13+y14+y34
      y234=y23+y24+y34

      wt = -2/y13 + (2*y12)/(y13*(y13 + y14)) - 2/y24 +
     -   (y12*(2*y12 + y14))/(y13*(y13 + y23)*y24) +
     -   (3*(2*y12 + y14 + y23))/(y13*y24) +
     -   (y12*(2*y12 + y24))/(y13*(y13 + y14)*(y13 + y23)) +
     -   (y12*(2*y12 + y23))/(y13*(y13 + y14)*(y14 + y24)) +
     -   (2*y12**3)/(y13*(y13 + y14)*(y13 + y23)*(y14 + y24)) +
     -   (y12*(2*y12 + y23))/(y13*y24*(y14 + y24)) +
     -   (2*y12**3)/(y13*(y13 + y23)*y24*(y14 + y24)) +
     -   (2*y12)/(y24*(y23 + y24)) +
     -   (y12*(2*y12 + y14))/((y13 + y23)*y24*(y23 + y24)) +
     -   (y12*(2*y12 + y13))/(y24*(y14 + y24)*(y23 + y24)) +
     -   (2*y12**3)/((y13 + y23)*y24*(y14 + y24)*(y23 + y24)) +
     -   (y12 + y23 + y24)/(y13 + y14 + y34)**2 +
     -   ((y12 + y23 + y24)*y34)/(y13*(y13 + y14 + y34)**2) +
     -   1/(y13 + y14 + y34) - (y23 + y24 - 2*y34)/
     -  (y13*(y13 + y14 + y34)) +
     -   (y12*(2*y12 + y23 + y34))/(y24*(y14 + y24)*
     -   (y13 + y14 + y34)) +
     -   (y12*(2*y12 + y24 + y34))/(y13*(y13 + y23)*
     -   (y13 + y14 + y34)) +
     -   (y12 + y13 + y14)/(y23 + y24 + y34)**2 +
     -   ((y12 + y13 + y14)*y34)/(y24*(y23 + y24 + y34)**2) +
     -   1/(y23 + y24 + y34) - (y13 + y14 - 2*y34)/
     -  (y24*(y23 + y24 + y34)) +
     -   (y12*(2*y12 + y13 + y34))/(y24*(y14 + y24)*
     -  (y23 + y24 + y34)) +
     -   (y12*(2*y12 + y14 + y34))/(y13*(y13 + y23)*
     -  (y23 + y24 + y34)) +
     -   (2*y12**3)/(y13*(y13 + y23)*
     -  (y13 + y14 + y34)*(y23 + y24 + y34)) +
     -   (2*y12**3)/(y24*(y14 + y24)*
     -  (y13 + y14 + y34)*(y23 + y24 + y34)) +
     -   (2*(y12 - y34))/((y13 + y14 + y34)*(y23 + y24 + y34)) +
     -   ((3*y12 - y13 - 2*y34)*y34)/
     -    (y24*(y13 + y14 + y34)*(y23 + y24 + y34)) +
     -   ((3*y12 - y24 - 2*y34)*y34)/
     -    (y13*(y13 + y14 + y34)*(y23 + y24 + y34)) +
     -   (-2*y12 + y13 - 2*y23 + 2*y34)/(y24*(y13 + y14 + y34)) +
     -   (-2*y12 - 2*y14 + y24 + 2*y34)/(y13*(y23 + y24 + y34)) +
     -   (4*y12**2 + y14**2 + 3*y12*(y14 - y34) - y14*y34 + y34**2)/
     -    (y13*y24*(y23 + y24 + y34)) +
     -   (4*y12**2 + y23**2 + 3*y12*(y23 - y34) - y23*y34 + y34**2)/
     -    (y13*y24*(y13 + y14 + y34)) +
     -   (2*y12**3 - 4*y12**2*y34 + 3*y12*y34**2 - y34**3)/
     -    (y13*y24*(y13 + y14 + y34)*(y23 + y24 + y34))


      Aqppq= 4d0*wt/y1234**2

      return
      end
      
cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc      
* same as function A40, but depending on i1,..,i4 and normalised 
* to s1234: A40i=A40/s1234 = (5.27)
* 22.06.06
      function A40i(i1,i3,i4,i2)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
*      
      s12=y(i1,i2)
      s13=y(i1,i3)
      s23=y(i2,i3)
      s14=y(i1,i4)
      s24=y(i2,i4)
      s34=y(i3,i4)
*
      s134=s13+s14+s34
      s234=s23+s24+s34
      s1234=s134+s234-s34+s12
*
      wt=0d0
*     
      wt =
     &  + s134**(-2) * ( 2*s12*s13*s14**2*s24 + s12*s13*s24*s34**2 +
     &    s12*s24*s34**3 + 2*s13*s14**2*s23*s24 + 2*s13*s14**2*s24**2
     &     + s13*s23*s24*s34**2 + s13*s24**2*s34**2 + s23*s24*s34**3 +
     &    s24**2*s34**3 )
      wt = wt + s134**(-1)*s234**(-1) * (  - 4*s12*s13*s14*s24*s34 - 4*
     &    s12*s13*s14*s24**2 - 3*s12*s13*s14*s34**2 + 6*s12*s13*s24*
     &    s34**2 + 3*s12*s13*s34**3 + 6*s12*s24*s34**3 + 3*s12*s24**2*
     &    s34**2 + 3*s12*s34**4 - 8*s12**2*s13*s24*s34 - 4*s12**2*s13*
     &    s34**2 - 4*s12**2*s24*s34**2 - 4*s12**2*s34**3 + 2*s12**3*
     &    s34**2 + 3*s13*s14*s24*s34**2 + 4*s13*s14*s24**2*s34 + s13*
     &    s14*s34**3 - 2*s13*s14**2*s24*s34 - s13*s14**2*s34**2 - 3*s13
     &    *s24*s34**3 - 3*s13*s24**2*s34**2 - 2*s13*s24**3*s34 - s13*
     &    s34**4 - 3*s24*s34**4 - 3*s24**2*s34**3 - s24**3*s34**2 -
     &    s34**5 )
      wt = wt + s134**(-1) * ( 2*s12*s13*s14*s34 + 2*s12*s13*s23*s34 -
     &    8*s12*s13*s24*s34 - 4*s12*s13*s34**2 + 3*s12*s23*s34**2 - 6*
     &    s12*s24*s34**2 - 3*s12*s34**3 + 2*s12**2*s13*s34 + 4*s12**2*
     &    s34**2 + 2*s13*s14*s23*s34 - 2*s13*s14*s24*s34 - 4*s13*s14*
     &    s24**2 - s13*s14*s34**2 + 2*s13*s14**2*s24 + s13*s14**2*s34
     &     - 3*s13*s23*s24*s34 - s13*s23*s34**2 + s13*s23**2*s34 + s13*
     &    s24*s34**2 - s13*s24**2*s34 + s13*s34**3 - 3*s23*s24*s34**2
     &     - s23*s34**3 + s23**2*s34**2 + 2*s24*s34**3 - s24**2*s34**2
     &     + s34**4 )
      wt = wt + s234**(-2) * ( 3*s12*s13*s24*s34**2 + 4*s12*s13*s24**2*
     &    s34 + 2*s12*s13*s24**3 + s12*s13*s34**3 + 3*s13*s14*s24*
     &    s34**2 + 4*s13*s14*s24**2*s34 + 2*s13*s14*s24**3 + s13*s14*
     &    s34**3 + 3*s13**2*s24*s34**2 + 4*s13**2*s24**2*s34 + 2*s13**2
     &    *s24**3 + s13**2*s34**3 )
      wt = wt + s234**(-1) * (  - 8*s12*s13*s24*s34 - 3*s12*s13*s34**2
     &     + 2*s12*s14*s24*s34 + 3*s12*s14*s34**2 - 6*s12*s24*s34**2 -
     &    2*s12*s24**2*s34 - 3*s12*s34**3 + 2*s12**2*s24*s34 + 4*s12**2
     &    *s34**2 - 5*s13*s14*s24*s34 - 4*s13*s14*s24**2 - 2*s13*s14*
     &    s34**2 + 2*s13*s24**2*s34 + 2*s13*s24**3 - 3*s13**2*s24*s34
     &     - 2*s13**2*s34**2 - 3*s14*s24*s34**2 - 2*s14*s24**2*s34 -
     &    s14*s34**3 + s14**2*s24*s34 + s14**2*s34**2 + 3*s24*s34**3 +
     &    3*s24**2*s34**2 + s24**3*s34 + s34**4 )
      wt = wt + 4*s12*s13*s34 + 2*s12*s14*s34 + 2*s12*s23*s34 + 6*s12*
     &    s24*s34 + 6*s12*s34**2 + 2*s12**2*s34 + 3*s13*s14*s34 - 2*s13
     &    *s24*s34 + 2*s13**2*s34 + 2*s14*s24*s34 + 3*s14*s34**2 +
     &    s14**2*s34 + 4*s23*s24*s34 + 3*s23*s34**2 + s23**2*s34 - 2*
     &    s24*s34**2 + s24**2*s34

        A40i=wt/s34**2/s13/s24/s1234
* 	
      return
      end
*******************************************************************
* same as function B40, but depending on i1,..,i4 and normalised 
* to s1234: B40i=B40/s1234 = (5.37)
      function B40i(i1,i3,i4,i2)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
*      
      s12=y(i1,i2)
      s13=y(i1,i3)
      s23=y(i2,i3)
      s14=y(i1,i4)
      s24=y(i2,i4)
      s34=y(i3,i4)
      s1234=s12+s13+s14+s23+s24+s34
      s134=s13+s14+s34
      s234=s23+s24+s34

      wt=0d0
      wt = wt +  ( 2*s12**2*s34 - 2*s12*s13*s24
     +     + s12*s13*s34 - 2*s12*s14*s23 + s12*s14*s34 + 
     +     s12*s23*s34 + 
     +    s12*s24*s34 + 2*s12*s34**2 - s13**2*s24 + 
     +    s13*s14*s23 + s13*
     +    s14*s24 + s13*s23*s24 - s13*s24**2 - 
     +    s14**2*s23 - s14*s23**2
     +     + s14*s23*s24 )/s134/s234

      wt = wt +  ( 2*s12*s13*s14 + s12*s13*s34 + s12*s14*
     +    s34 - s13**2*s24 + s13*s14*s23 + s13*s14*s24 + 
     +   s13*s23*s34 - 
     +    s14**2*s23 + s14*s24*s34 )/s134**2

      wt = wt +  ( 2*s12*s23*s24 + s12*s23*s34 + s12*s24*
     +    s34 + s13*s23*s24 + s13*s23*s34 - s13*s24**2 - 
     +    s14*s23**2 + 
     +    s14*s23*s24 + s14*s24*s34 )/s234**2

      B40i= wt/s34**2/s1234
    
      return
      end
*
*******************************************************************
* same as function C40, but depending on i1,..,i4 and normalised 
* to s1234: C40i= (5.42)
      function C40i(i1,i3,i4,i2)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
*      
      s12=y(i1,i2)
      s13=y(i1,i3)
      s23=y(i2,i3)
      s14=y(i1,i4)
      s24=y(i2,i4)
      s34=y(i3,i4)
      s1234=s12+s13+s14+s23+s24+s34
      s134=s13+s14+s34
      s234=s23+s24+s34
      s123=s23+s12+s13
*
      wt=0d0
      wt = wt + s23**(-1)*s34**(-1)*s123**(-1)*s134**(-1) * 
     +  ( 2*s12*s13
     +    *s14 + 2*s12*s13*s34 + 2*s13*s14*s23 + 2*s13*s23*s34 )

      wt = wt + s23**(-1)*s34**(-1)*s123**(-1)*s234**(-1) * 
     + ( s12**2*
     +    s34 - s12*s13*s24 - s12*s14*s23 + s12*s14*s34 + 
     +  s12*s23*s34
     +     + s12*s34**2 + s13*s14*s24 - s13*s23*s24 - s13*s24*s34 - 
     +    s14**2*s23 - s14*s23**2 - s14*s23*s34 )

      wt = wt + s23**(-1)*s34**(-1)*s134**(-1)*s234**(-1) * 
     + (  - s12**2
     +    *s34 + s12*s13*s24 + s12*s14*s23 - s12*s14*s34 - 
     +    s12*s23*s34
     +     - s12*s34**2 - s13*s14*s24 - s13*s23*s24 - s13*s24*s34 + 
     +    s14**2*s23 + s14*s23**2 + s14*s23*s34 )

      wt = wt + s23**(-1)*s34**(-1)*s234**(-2) * 
     + (  - 2*s12*s23*s24 - 2
     +    *s12*s24*s34 + 2*s13*s24**2 - 2*s14*s23*s24 - 
     +    2*s14*s24*s34 )

      C40i=-wt/2.d0/s1234
c  
      return
      end

************************************************************************
*  from /ana/D40.sub (finite part)
      function D40i(i1,i2,i3,i4)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      s12=y(i1,i2)
      s13=y(i1,i3)
      s14=y(i1,i4)
      s23=y(i2,i3)
      s24=y(i2,i4)
      s34=y(i3,i4)
      s134=s13+s14+s34
      s123=s23+s12+s13
      s124=s12+s14+s24
      s234=s23+s24+s34
      
      s1234=s12+s13+s14+s23+s24+s34
      
      wt=0d0
      
       wt =
     &  + s123**(-2) * ( 4*s12*s13**2*s14*s24*s34**3 + 2*s12*s13**2*s14
     &    *s24**2*s34**2 + 2*s12*s13**2*s14*s34**4 + 4*s12*s13**2*
     &    s14**2*s24*s34**2 + 4*s12*s13**2*s14**2*s34**3 + 2*s12*s13**2
     &    *s14**3*s34**2 + 2*s12*s14*s23**2*s24*s34**3 + s12*s14*s23**2
     &    *s24**2*s34**2 + s12*s14*s23**2*s34**4 + 2*s12*s14**2*s23**2*
     &    s24*s34**2 + 2*s12*s14**2*s23**2*s34**3 + s12*s14**3*s23**2*
     &    s34**2 + 2*s14*s23**3*s24*s34**3 + s14*s23**3*s24**2*s34**2
     &     + s14*s23**3*s34**4 + 2*s14**2*s23**3*s24*s34**2 + 2*s14**2*
     &    s23**3*s34**3 + s14**3*s23**3*s34**2 )
      wt = wt + s123**(-1)*s124**(-1) * ( 6*s12*s14*s23*s24*s34**4 + 9*
     &    s12*s14*s23*s24**2*s34**3 + 4*s12*s14*s23*s24**3*s34**2 + s12
     &    *s14*s23*s34**5 - 9*s12*s14*s23**2*s24*s34**3 - 9*s12*s14*
     &    s23**2*s24**2*s34**2 + 6*s12*s14*s23**3*s24*s34**2 - s12*s14*
     &    s23**4*s34**2 + 9*s12*s14**2*s23*s24*s34**3 + 6*s12*s14**2*
     &    s23*s24**2*s34**2 + 3*s12*s14**2*s23*s34**4 - 9*s12*s14**2*
     &    s23**2*s24*s34**2 + 3*s12*s14**2*s23**3*s34**2 + 5*s12*s14**3
     &    *s23*s24*s34**2 + 3*s12*s14**3*s23*s34**3 - 3*s12*s14**3*
     &    s23**2*s34**2 + 2*s12*s14**4*s23*s34**2 + s12*s23*s24*s34**5
     &     + 3*s12*s23*s24**2*s34**4 + 3*s12*s23*s24**3*s34**3 + s12*
     &    s23*s24**4*s34**2 - 3*s12*s23**2*s24*s34**4 - 6*s12*s23**2*
     &    s24**2*s34**3 - 3*s12*s23**2*s24**3*s34**2 + 3*s12*s23**3*s24
     &    *s34**3 + 3*s12*s23**3*s24**2*s34**2 - s12*s23**4*s24*s34**2
     &     )
      wt = wt + s123**(-1)*s134**(-1) * ( 12*s12*s14*s23*s24*s34**4 + 9
     &    *s12*s14*s23*s24**2*s34**3 + 2*s12*s14*s23*s24**3*s34**2 + 5*
     &    s12*s14*s23*s34**5 - 6*s12*s14*s23**2*s24*s34**3 - 8*s12*s14*
     &    s23**2*s34**4 + 3*s12*s14*s23**3*s34**3 + 18*s12*s14**2*s23*
     &    s24*s34**3 + 9*s12*s14**2*s23*s24**2*s34**2 + s12*s14**2*s23*
     &    s24**3*s34 + 10*s12*s14**2*s23*s34**4 - 3*s12*s14**2*s23**2*
     &    s24*s34**2 - 12*s12*s14**2*s23**2*s34**3 + 3*s12*s14**2*
     &    s23**3*s34**2 + 12*s12*s14**3*s23*s24*s34**2 + 3*s12*s14**3*
     &    s23*s24**2*s34 + 11*s12*s14**3*s23*s34**3 - 8*s12*s14**3*
     &    s23**2*s34**2 + s12*s14**3*s23**3*s34 + 3*s12*s14**4*s23*s24*
     &    s34 + 7*s12*s14**4*s23*s34**2 - 2*s12*s14**4*s23**2*s34 + 2*
     &    s12*s14**5*s23*s34 + 3*s12*s23*s24*s34**5 + 3*s12*s23*s24**2*
     &    s34**4 + s12*s23*s24**3*s34**3 + s12*s23*s34**6 - 3*s12*
     &    s23**2*s24*s34**4 - 2*s12*s23**2*s34**5 + s12*s23**3*s34**4
     &     + 3*s14*s23**2*s24**2*s34**3 + 2*s14*s23**2*s24**3*s34**2 + 
     &    3*s14**2*s23**2*s24*s34**3 )
      wt = wt + s123**(-1)*s134**(-1) * ( 6*s14**2*s23**2*s24**2*s34**2
     &     + s14**2*s23**2*s24**3*s34 + 6*s14**3*s23**2*s24*s34**2 + 3*
     &    s14**3*s23**2*s24**2*s34 + s14**3*s23**2*s34**3 + 3*s14**4*
     &    s23**2*s24*s34 + 2*s14**4*s23**2*s34**2 + s14**5*s23**2*s34
     &     + s23**2*s24**3*s34**3 )
      wt = wt + s123**(-1)*s234**(-1) * (  - 5*s12*s13*s14*s23**2*s24*
     &    s34**2 - 2*s12*s13*s14*s23**2*s24**2*s34 - 3*s12*s13*s14*
     &    s23**2*s34**3 - 2*s12*s13*s14**2*s23*s34**3 - 4*s12*s13*
     &    s14**2*s23**2*s24*s34 - 10*s12*s13*s14**2*s23**2*s34**2 - 4*
     &    s12*s13*s14**3*s23*s34**2 - 6*s12*s13*s14**3*s23**2*s34 - 4*
     &    s12*s13*s14**3*s34**3 + s12*s13**2*s14*s23**2*s24*s34 + 3*s12
     &    *s13**2*s14*s23**2*s34**2 - 8*s12*s13**2*s14**2*s23*s34**2 - 
     &    4*s12*s13**2*s14**2*s23**2*s34 - 2*s12*s13**3*s14*s23**2*s34
     &     + s12*s14*s23**2*s24*s34**3 - s12*s14*s23**2*s24**2*s34**2
     &     - s12*s14*s23**2*s24**3*s34 + s12*s14*s23**2*s34**4 - 2*s12*
     &    s14**2*s23*s34**4 + s12*s14**2*s23**2*s24*s34**2 - 4*s12*
     &    s14**2*s23**2*s24**2*s34 + 2*s12*s14**2*s23**2*s34**3 - 6*s12
     &    *s14**3*s23**2*s24*s34 + 6*s12*s14**3*s23**2*s34**2 - 8*s12*
     &    s14**4*s23*s34**2 - 4*s12*s14**4*s23**2*s34 + s14*s23**2*s24*
     &    s34**4 + 3*s14*s23**2*s24**2*s34**3 + 3*s14*s23**2*s24**3*
     &    s34**2 )
      wt = wt + s123**(-1)*s234**(-1) * ( s14*s23**2*s24**4*s34 + 6*
     &    s14**2*s23**2*s24*s34**3 + 9*s14**2*s23**2*s24**2*s34**2 + 5*
     &    s14**2*s23**2*s24**3*s34 + s14**2*s23**2*s34**4 + 9*s14**3*
     &    s23**2*s24*s34**2 + 9*s14**3*s23**2*s24**2*s34 + 3*s14**3*
     &    s23**2*s34**3 + 7*s14**4*s23**2*s24*s34 + 3*s14**4*s23**2*
     &    s34**2 + 2*s14**5*s23**2*s34 )
      wt = wt + s123**(-1) * ( 5*s12*s13*s14*s23*s24*s34**2 - 3*s12*s13
     &    *s14*s23*s34**3 + s12*s13*s14*s23**2*s24*s34 - 3*s12*s13*s14*
     &    s23**2*s34**2 - 4*s12*s13*s14*s24*s34**3 - 4*s12*s13*s14*
     &    s34**4 + 2*s12*s13*s14**2*s23*s24*s34 + 2*s12*s13*s14**2*s23*
     &    s34**2 - 2*s12*s13*s14**2*s23**2*s34 - 8*s12*s13*s14**2*
     &    s34**3 + 4*s12*s13*s14**3*s23*s34 + s12*s13*s23*s24**2*s34**2
     &     - s12*s13*s23*s34**4 - 2*s12*s13*s23**2*s34**3 + s12*s13**2*
     &    s14*s23*s24*s34 - 7*s12*s13**2*s14*s23*s34**2 + 4*s12*s13**2*
     &    s14*s24*s34**2 + 4*s12*s13**2*s14*s34**3 + 2*s12*s13**2*
     &    s14**2*s23*s34 + 4*s12*s13**2*s14**2*s34**2 - 2*s12*s13**2*
     &    s23*s24*s34**2 - 2*s12*s13**2*s23*s34**3 + 2*s12*s13**3*s14*
     &    s23*s34 - 19*s12*s14*s23*s24*s34**3 - 11*s12*s14*s23*s24**2*
     &    s34**2 - 10*s12*s14*s23*s34**4 + 11*s12*s14*s23**2*s24*s34**2
     &     + s12*s14*s23**2*s24**2*s34 + 9*s12*s14*s23**2*s34**3 - 3*
     &    s12*s14*s23**3*s34**2 - 21*s12*s14**2*s23*s24*s34**2 - 18*s12
     &    *s14**2*s23*s34**3 )
      wt = wt + s123**(-1) * ( 2*s12*s14**2*s23**2*s24*s34 + 12*s12*
     &    s14**2*s23**2*s34**2 - s12*s14**2*s23**3*s34 + s12*s14**3*s23
     &    *s24*s34 - 21*s12*s14**3*s23*s34**2 + 3*s12*s14**3*s23**2*s34
     &     - 6*s12*s23*s24*s34**4 - 6*s12*s23*s24**2*s34**3 - 2*s12*s23
     &    *s24**3*s34**2 - 2*s12*s23*s34**5 + 6*s12*s23**2*s24*s34**3
     &     + 2*s12*s23**2*s24**2*s34**2 + 2*s12*s23**2*s34**4 - s12*
     &    s23**3*s24*s34**2 - s12*s23**3*s34**3 - 5*s14*s23**2*s24*
     &    s34**3 - 7*s14*s23**2*s24**2*s34**2 - s14*s23**2*s24**3*s34
     &     - 2*s14*s23**2*s34**4 + 4*s14*s23**3*s24*s34**2 + s14*s23**3
     &    *s24**2*s34 + 3*s14*s23**3*s34**3 - 13*s14**2*s23**2*s24*
     &    s34**2 - 4*s14**2*s23**2*s24**2*s34 - 6*s14**2*s23**2*s34**3
     &     + 2*s14**2*s23**3*s24*s34 + 4*s14**2*s23**3*s34**2 - 5*
     &    s14**3*s23**2*s24*s34 - 7*s14**3*s23**2*s34**2 + s14**3*
     &    s23**3*s34 - 2*s14**4*s23**2*s34 - s23**2*s24**3*s34**2 )
      wt = wt + s124**(-2) * ( 4*s12*s13*s14*s23**2*s34**3 + 4*s12*s13*
     &    s14*s23**3*s34**2 + 2*s12*s13*s23**2*s24*s34**3 + 2*s12*s13*
     &    s23**3*s24*s34**2 + 2*s12*s13**2*s14*s23**2*s34**2 + s12*
     &    s13**2*s23**2*s24*s34**2 + 2*s12*s14*s23**2*s34**4 + 4*s12*
     &    s14*s23**3*s34**3 + 2*s12*s14*s23**4*s34**2 + s12*s23**2*s24*
     &    s34**4 + 2*s12*s23**3*s24*s34**3 + s12*s23**4*s24*s34**2 + 2*
     &    s13*s14*s23**2*s24*s34**3 + 2*s13*s14*s23**3*s24*s34**2 + 
     &    s13**2*s14*s23**2*s24*s34**2 + s14*s23**2*s24*s34**4 + 2*s14*
     &    s23**3*s24*s34**3 + s14*s23**4*s24*s34**2 )
      wt = wt + s124**(-1)*s134**(-1) * ( 3*s12*s14*s23**2*s24*s34**3
     &     - 3*s12*s14*s23**2*s24**2*s34**2 + s12*s14*s23**2*s24**3*s34
     &     - s12*s14*s23**2*s34**4 - 9*s12*s14*s23**3*s24*s34**2 + 3*
     &    s12*s14*s23**3*s24**2*s34 + 3*s12*s14*s23**4*s24*s34 + s12*
     &    s14*s23**5*s34 + 3*s12*s14**2*s23**2*s24*s34**2 - 2*s12*
     &    s14**2*s23**2*s24**2*s34 - 3*s12*s14**2*s23**2*s34**3 - 3*s12
     &    *s14**2*s23**3*s24*s34 - 3*s12*s14**2*s23**4*s34 - s12*s14**3
     &    *s23**2*s24*s34 - 3*s12*s14**3*s23**2*s34**2 + 3*s12*s14**3*
     &    s23**3*s34 - 2*s12*s14**4*s23**2*s34 - s14*s23**2*s24*s34**4
     &     + 3*s14*s23**2*s24**2*s34**3 - 3*s14*s23**2*s24**3*s34**2 + 
     &    s14*s23**2*s24**4*s34 + 3*s14*s23**3*s24*s34**3 - 6*s14*
     &    s23**3*s24**2*s34**2 + 3*s14*s23**3*s24**3*s34 - 3*s14*s23**4
     &    *s24*s34**2 + 3*s14*s23**4*s24**2*s34 + s14*s23**5*s24*s34 )
      wt = wt + s124**(-1)*s234**(-1) * (  - 8*s12*s13*s14*s23*s34**4
     &     + 10*s12*s13*s14*s23**2*s24*s34**2 - 4*s12*s13*s14*s23**2*
     &    s24**2*s34 - 8*s12*s13*s14*s23**2*s34**3 + 4*s12*s13*s14**2*
     &    s23*s34**3 + 4*s12*s13*s14**2*s23**2*s24*s34 + 4*s12*s13*
     &    s14**2*s23**2*s34**2 + 5*s12*s13*s23*s34**5 - 4*s12*s13*
     &    s23**2*s24*s34**3 + 4*s12*s13*s23**2*s24**2*s34**2 - s12*s13*
     &    s23**2*s24**3*s34 + 5*s12*s13*s23**2*s34**4 - 6*s12*s13**2*
     &    s14*s23*s34**3 + 6*s12*s13**2*s14*s23**2*s24*s34 - 2*s12*
     &    s13**2*s14*s23**2*s34**2 + 9*s12*s13**2*s23*s34**4 - 6*s12*
     &    s13**2*s23**2*s24*s34**2 + 3*s12*s13**2*s23**2*s24**2*s34 + 9
     &    *s12*s13**2*s23**2*s34**3 + 7*s12*s13**3*s23*s34**3 - 3*s12*
     &    s13**3*s23**2*s24*s34 + 7*s12*s13**3*s23**2*s34**2 + 2*s12*
     &    s13**4*s23*s34**2 + 2*s12*s13**4*s23**2*s34 - 3*s12*s14*s23*
     &    s34**5 + 3*s12*s14*s23**2*s24*s34**3 - 3*s12*s14*s23**2*
     &    s24**2*s34**2 + 2*s12*s14*s23**2*s24**3*s34 - 3*s12*s14*
     &    s23**2*s34**4 )
      wt = wt + s124**(-1)*s234**(-1) * ( 3*s12*s14**2*s23*s34**4 - 3*
     &    s12*s14**2*s23**2*s24*s34**2 + s12*s14**2*s23**2*s24**2*s34
     &     + 3*s12*s14**2*s23**2*s34**3 - 2*s12*s14**3*s23*s34**3 + 2*
     &    s12*s14**3*s23**2*s24*s34 - 2*s12*s14**3*s23**2*s34**2 + s12*
     &    s23*s34**6 - s12*s23**2*s24*s34**4 + s12*s23**2*s24**2*s34**3
     &     - s12*s23**2*s24**3*s34**2 + s12*s23**2*s34**5 + s13*s14*s23
     &    *s34**5 - 2*s13*s14*s23**2*s24*s34**3 - s13*s14*s23**2*s24**2
     &    *s34**2 - 5*s13*s14*s23**2*s24**3*s34 + s13*s14*s23**2*s34**4
     &     + 3*s13**2*s14*s23*s34**4 + 9*s13**2*s14*s23**2*s24**2*s34
     &     + 3*s13**2*s14*s23**2*s34**3 + 3*s13**3*s14*s23*s34**3 - 7*
     &    s13**3*s14*s23**2*s24*s34 + 3*s13**3*s14*s23**2*s34**2 + 2*
     &    s13**4*s14*s23*s34**2 + 2*s13**4*s14*s23**2*s34 + s14*s23**2*
     &    s24**4*s34 )
      wt = wt + s124**(-1) * ( s12*s13*s14*s23*s24*s34**2 + 9*s12*s13*
     &    s14*s23*s34**3 + 5*s12*s13*s14*s23**2*s24*s34 + 4*s12*s13*s14
     &    *s23**2*s34**2 + s12*s13*s14*s23**3*s34 - 4*s12*s13*s14**2*
     &    s23**2*s34 + 5*s12*s13*s23*s24*s34**3 + s12*s13*s23*s24**2*
     &    s34**2 - s12*s13*s23*s34**4 - 2*s12*s13*s23**2*s24*s34**2 + 
     &    s12*s13*s23**2*s24**2*s34 + 2*s12*s13*s23**2*s34**3 - s12*s13
     &    *s23**3*s24*s34 + s12*s13*s23**4*s34 + 4*s12*s13**2*s14*s23*
     &    s34**2 - 2*s12*s13**2*s14*s23**2*s34 + 2*s12*s13**2*s23*s24*
     &    s34**2 - 2*s12*s13**2*s23*s34**3 - 3*s12*s13**2*s23**2*s24*
     &    s34 + 6*s12*s13**2*s23**2*s34**2 + 3*s12*s13**2*s23**3*s34 - 
     &    s12*s13**3*s23*s34**2 + 4*s12*s13**3*s23**2*s34 + 5*s12*s14*
     &    s23*s24*s34**3 + 3*s12*s14*s23*s24**2*s34**2 + 6*s12*s14*s23*
     &    s34**4 - 4*s12*s14*s23**2*s24*s34**2 + 7*s12*s14*s23**2*
     &    s34**3 + 4*s12*s14*s23**3*s24*s34 + 7*s12*s14*s23**3*s34**2
     &     + 3*s12*s14*s23**4*s34 + 3*s12*s14**2*s23*s24*s34**2 + s12*
     &    s14**2*s23*s34**3 )
      wt = wt + s124**(-1) * (  - 4*s12*s14**2*s23**3*s34 + 2*s12*
     &    s14**3*s23*s34**2 + 4*s12*s23*s24*s34**4 + 3*s12*s23*s24**2*
     &    s34**3 + s12*s23*s24**3*s34**2 - s12*s23**2*s24*s34**3 - s12*
     &    s23**2*s24**2*s34**2 + 3*s12*s23**3*s24*s34**2 - 2*s12*s23**3
     &    *s34**3 - s12*s23**4*s34**2 - s13*s14*s23**2*s24*s34**2 + 6*
     &    s13*s14*s23**2*s24**2*s34 + 2*s13*s14*s23**3*s34**2 + 4*s13*
     &    s14*s23**4*s34 - 7*s13**2*s14*s23**2*s24*s34 + 6*s13**2*s14*
     &    s23**2*s34**2 + 7*s13**2*s14*s23**3*s34 + s13**3*s14*s23*
     &    s34**2 + 6*s13**3*s14*s23**2*s34 + 3*s14*s23**2*s24*s34**3 - 
     &    s14*s23**2*s24**2*s34**2 - s14*s23**2*s34**4 - s14*s23**3*s24
     &    *s34**2 + 4*s14*s23**3*s24**2*s34 - 2*s14*s23**3*s34**3 + 3*
     &    s14*s23**4*s24*s34 + s14*s23**5*s34 )
      wt = wt + s134**(-2) * ( 3*s12*s14*s23**2*s24**2*s34**2 + 6*s12*
     &    s14*s23**3*s24*s34**2 + 3*s12*s14*s23**4*s34**2 + 4*s12*
     &    s14**2*s23**2*s24**2*s34 + 8*s12*s14**2*s23**3*s24*s34 + 4*
     &    s12*s14**2*s23**4*s34 + 2*s12*s14**3*s23**2*s24**2 + 4*s12*
     &    s14**3*s23**3*s24 + 2*s12*s14**3*s23**4 + s12*s23**2*s24**2*
     &    s34**3 + 2*s12*s23**3*s24*s34**3 + s12*s23**4*s34**3 + 6*
     &    s12**2*s14*s23**2*s24*s34**2 + 6*s12**2*s14*s23**3*s34**2 + 8
     &    *s12**2*s14**2*s23**2*s24*s34 + 8*s12**2*s14**2*s23**3*s34 + 
     &    4*s12**2*s14**3*s23**2*s24 + 4*s12**2*s14**3*s23**3 + 2*
     &    s12**2*s23**2*s24*s34**3 + 2*s12**2*s23**3*s34**3 + 3*s12**3*
     &    s14*s23**2*s34**2 + 4*s12**3*s14**2*s23**2*s34 + 2*s12**3*
     &    s14**3*s23**2 + s12**3*s23**2*s34**3 )
      wt = wt + s134**(-1)*s234**(-1) * ( 4*s12*s14*s23*s34**5 + 3*s12*
     &    s14*s23**2*s34**4 + 6*s12*s14**2*s23*s34**4 + 3*s12*s14**2*
     &    s23**2*s34**3 + 5*s12*s14**3*s23*s34**3 + 2*s12*s14**3*s23**2
     &    *s34**2 + 2*s12*s14**4*s23*s34**2 + s12*s23*s34**6 + s12*
     &    s23**2*s34**5 - 12*s12**2*s14*s23*s34**4 - 3*s12**2*s14*
     &    s23**2*s24*s34**2 - 2*s12**2*s14*s23**2*s24**2*s34 - 12*
     &    s12**2*s14*s23**2*s34**3 - 12*s12**2*s14**2*s23*s34**3 - 2*
     &    s12**2*s14**2*s23**2*s24*s34 - 12*s12**2*s14**2*s23**2*s34**2
     &     - 4*s12**2*s14**3*s23*s34**2 - 8*s12**2*s14**3*s23**2*s34 - 
     &    5*s12**2*s23*s34**5 + s12**2*s23**2*s24*s34**3 - s12**2*
     &    s23**2*s24**2*s34**2 - 4*s12**2*s23**2*s34**4 + 12*s12**3*s14
     &    *s23*s34**3 - 4*s12**3*s14*s23**2*s24*s34 + 12*s12**3*s14*
     &    s23**2*s34**2 + 6*s12**3*s14**2*s23*s34**2 - 4*s12**3*s14**2*
     &    s23**2*s24 + 9*s12**3*s23*s34**4 - 3*s12**3*s23**2*s24*s34**2
     &     + 6*s12**3*s23**2*s34**3 - 4*s12**4*s14*s23*s34**2 - 8*
     &    s12**4*s14*s23**2*s34 )
      wt = wt + s134**(-1)*s234**(-1) * (  - 7*s12**4*s23*s34**3 - 4*
     &    s12**4*s23**2*s34**2 + 2*s12**5*s23*s34**2 )
      wt = wt + s134**(-1) * ( 12*s12*s14*s23*s24*s34**3 + 6*s12*s14*
     &    s23*s24**2*s34**2 + s12*s14*s23*s24**3*s34 + 7*s12*s14*s23**2
     &    *s24*s34**2 - 6*s12*s14*s23**2*s24**2*s34 - 5*s12*s14*s23**2*
     &    s34**3 - 8*s12*s14*s23**3*s24*s34 + 14*s12*s14*s23**3*s34**2
     &     - 3*s12*s14*s23**4*s34 + 12*s12*s14**2*s23*s24*s34**2 + 3*
     &    s12*s14**2*s23*s24**2*s34 + 8*s12*s14**2*s23**2*s24*s34 - 4*
     &    s12*s14**2*s23**2*s24**2 - 8*s12*s14**2*s23**2*s34**2 - 4*s12
     &    *s14**2*s23**3*s24 + 11*s12*s14**2*s23**3*s34 + 4*s12*s14**3*
     &    s23*s24*s34 + 4*s12*s14**3*s23**2*s24 - 4*s12*s14**3*s23**2*
     &    s34 + 4*s12*s14**3*s23**3 + 4*s12*s23*s24*s34**4 + 3*s12*s23*
     &    s24**2*s34**3 + s12*s23*s24**3*s34**2 + 3*s12*s23**2*s24*
     &    s34**3 - 2*s12*s23**2*s24**2*s34**2 - s12*s23**2*s34**4 - 4*
     &    s12*s23**3*s24*s34**2 + 3*s12*s23**3*s34**3 - 2*s12*s23**4*
     &    s34**2 + 2*s12**2*s14*s23*s24*s34**2 + 3*s12**2*s14*s23*
     &    s24**2*s34 + 14*s12**2*s14*s23*s34**3 - 15*s12**2*s14*s23**2*
     &    s24*s34 )
      wt = wt + s134**(-1) * ( 14*s12**2*s14*s23**2*s34**2 - 11*s12**2*
     &    s14*s23**3*s34 + s12**2*s14**2*s23*s24*s34 + 13*s12**2*s14**2
     &    *s23*s34**2 - 8*s12**2*s14**2*s23**2*s24 + 9*s12**2*s14**2*
     &    s23**2*s34 + 4*s12**2*s14**3*s23*s34 + 4*s12**2*s14**3*s23**2
     &     + 4*s12**2*s23*s24**2*s34**2 + 6*s12**2*s23*s34**4 - 5*
     &    s12**2*s23**2*s24*s34**2 + 3*s12**2*s23**2*s34**3 - 5*s12**2*
     &    s23**3*s34**2 + 4*s12**3*s14*s23*s24*s34 - 6*s12**3*s14*s23*
     &    s34**2 - 14*s12**3*s14*s23**2*s34 - 2*s12**3*s14**2*s23*s34
     &     + 7*s12**3*s23*s24*s34**2 - 7*s12**3*s23*s34**3 - 3*s12**3*
     &    s23**2*s34**2 + 2*s12**4*s14*s23*s34 + 6*s12**4*s23*s34**2 - 
     &    3*s14*s23**2*s24*s34**3 + 4*s14*s23**2*s24**2*s34**2 - s14*
     &    s23**2*s24**3*s34 + 6*s14*s23**3*s24*s34**2 - 3*s14*s23**3*
     &    s24**2*s34 - s14*s23**3*s34**3 - 3*s14*s23**4*s24*s34 + 2*s14
     &    *s23**4*s34**2 - s14*s23**5*s34 - s14**2*s23**2*s24*s34**2 + 
     &    2*s14**2*s23**2*s24**2*s34 + 3*s14**2*s23**3*s24*s34 - 2*
     &    s14**2*s23**3*s34**2 )
      wt = wt + s134**(-1) * ( 2*s14**2*s23**4*s34 + s14**3*s23**2*s24*
     &    s34 + s14**3*s23**2*s34**2 - s14**3*s23**3*s34 + s14**4*
     &    s23**2*s34 )
      wt = wt + s234**(-2) * ( 8*s12*s13*s14**2*s23*s34**3 + 4*s12*s13*
     &    s14**2*s23**2*s24**2 + 8*s12*s13*s14**2*s23**2*s34**2 + 4*s12
     &    *s13*s14**2*s34**4 + 4*s12*s13**2*s14*s23*s34**3 + 2*s12*
     &    s13**2*s14*s23**2*s24**2 + 4*s12*s13**2*s14*s23**2*s34**2 + 2
     &    *s12*s13**2*s14*s34**4 + 4*s12*s14**3*s23*s34**3 + 2*s12*
     &    s14**3*s23**2*s24**2 + 4*s12*s14**3*s23**2*s34**2 + 2*s12*
     &    s14**3*s34**4 + 8*s12**2*s13*s14*s23*s34**3 + 4*s12**2*s13*
     &    s14*s23**2*s24**2 + 8*s12**2*s13*s14*s23**2*s34**2 + 4*s12**2
     &    *s13*s14*s34**4 + 8*s12**2*s14**2*s23*s34**3 + 4*s12**2*
     &    s14**2*s23**2*s24**2 + 8*s12**2*s14**2*s23**2*s34**2 + 4*
     &    s12**2*s14**2*s34**4 + 4*s12**3*s14*s23*s34**3 + 2*s12**3*s14
     &    *s23**2*s24**2 + 4*s12**3*s14*s23**2*s34**2 + 2*s12**3*s14*
     &    s34**4 )
      wt = wt + s234**(-1) * ( 5*s12*s13*s14*s23*s34**3 + 4*s12*s13*s14
     &    *s23**2*s24**2 + 4*s12*s13*s14*s23**2*s34**2 + 4*s12*s13*s14*
     &    s34**4 - 10*s12*s13*s14**2*s23*s34**2 - 4*s12*s13*s14**2*
     &    s23**2*s24 - 4*s12*s13*s14**2*s23**2*s34 - 8*s12*s13*s14**2*
     &    s34**3 + 6*s12*s13*s23*s34**4 - 4*s12*s13*s23**2*s24*s34**2
     &     + s12*s13*s23**2*s24**2*s34 + 5*s12*s13*s23**2*s34**3 - 8*
     &    s12*s13**2*s14*s23*s34**2 - 2*s12*s13**2*s14*s23**2*s34 - 4*
     &    s12*s13**2*s14*s34**3 + 7*s12*s13**2*s23*s34**3 - 3*s12*
     &    s13**2*s23**2*s24*s34 + 5*s12*s13**2*s23**2*s34**2 + 6*s12*
     &    s13**3*s23*s34**2 + 4*s12*s13**3*s23**2*s34 - 5*s12*s14*s23*
     &    s34**4 + 3*s12*s14*s23**2*s24*s34**2 - s12*s14*s23**2*s24**2*
     &    s34 - 3*s12*s14*s23**2*s34**3 + 8*s12*s14**2*s23*s34**3 - 3*
     &    s12*s14**2*s23**2*s24*s34 + 4*s12*s14**2*s23**2*s24**2 + 15*
     &    s12*s14**2*s23**2*s34**2 + 4*s12*s14**2*s34**4 - 16*s12*
     &    s14**3*s23*s34**2 - 4*s12*s14**3*s23**2*s24 - 6*s12*s14**3*
     &    s23**2*s34 )
      wt = wt + s234**(-1) * (  - s12*s23**2*s24*s34**3 + s12*s23**2*
     &    s24**2*s34**2 - 12*s12**2*s13*s14*s23*s34**2 - 12*s12**2*s13*
     &    s14*s23**2*s34 - 4*s12**2*s13*s14*s34**3 - s12**2*s13*s23**2*
     &    s24*s34 + s12**2*s13*s23**2*s34**2 + 10*s12**2*s13**2*s23*
     &    s34**2 + 6*s12**2*s13**2*s23**2*s34 + 17*s12**2*s14*s23*
     &    s34**3 + s12**2*s14*s23**2*s24*s34 + 4*s12**2*s14*s23**2*
     &    s24**2 + 19*s12**2*s14*s23**2*s34**2 + 4*s12**2*s14*s34**4 - 
     &    10*s12**2*s14**2*s23*s34**2 - 8*s12**2*s14**2*s23**2*s24 - 6*
     &    s12**2*s14**2*s23**2*s34 + 6*s12**2*s23*s34**4 - 2*s12**2*
     &    s23**2*s24*s34**2 + s12**2*s23**2*s24**2*s34 + 5*s12**2*
     &    s23**2*s34**3 + 10*s12**3*s13*s23*s34**2 + 4*s12**3*s13*
     &    s23**2*s34 - 12*s12**3*s14*s23*s34**2 - 14*s12**3*s14*s23**2*
     &    s34 - 7*s12**3*s23*s34**3 + 2*s12**3*s23**2*s24*s34 - 4*
     &    s12**3*s23**2*s34**2 + 6*s12**4*s23*s34**2 + 2*s12**4*s23**2*
     &    s34 + s13*s14*s23*s34**4 + 2*s13*s14*s23**2*s24*s34**2 + 6*
     &    s13*s14*s23**2*s24**2*s34 )
      wt = wt + s234**(-1) * ( 2*s13*s14*s23**2*s34**3 + s13*s14**2*s23
     &    *s34**3 + 2*s13*s14**2*s23**2*s34**2 + 4*s13*s14**3*s23*
     &    s34**2 + 10*s13*s14**3*s23**2*s34 + 3*s13**2*s14*s23*s34**3
     &     - 7*s13**2*s14*s23**2*s24*s34 + s13**2*s14*s23**2*s34**2 + 6
     &    *s13**2*s14**2*s23*s34**2 + 10*s13**2*s14**2*s23**2*s34 + 4*
     &    s13**3*s14*s23*s34**2 + 6*s13**3*s14*s23**2*s34 + s14*s23**2*
     &    s24*s34**3 + 2*s14*s23**2*s24**2*s34**2 + s14**2*s23*s34**4
     &     + 4*s14**2*s23**2*s24*s34**2 + 6*s14**2*s23**2*s24**2*s34 + 
     &    2*s14**2*s23**2*s34**3 - 2*s14**3*s23*s34**3 + 7*s14**3*
     &    s23**2*s24*s34 + s14**3*s23**2*s34**2 + 2*s14**4*s23*s34**2
     &     + 6*s14**4*s23**2*s34 )
      wt = wt + 22*s12*s13*s14*s23*s24*s34 + 14*s12*s13*s14*s23*s34**2
     &     + 12*s12*s13*s14*s23**2*s34 - 8*s12*s13*s14*s34**3 + 14*s12*
     &    s13*s14**2*s23*s34 + 14*s12*s13*s23*s24*s34**2 + 6*s12*s13*
     &    s23*s24**2*s34 + 4*s12*s13*s23*s34**3 + 15*s12*s13*s23**2*s24
     &    *s34 + 15*s12*s13*s23**2*s34**2 + 12*s12*s13*s23**3*s34 + 14*
     &    s12*s13**2*s14*s23*s34 + 2*s12*s13**2*s14*s34**2 + 9*s12*
     &    s13**2*s23*s24*s34 + 11*s12*s13**2*s23*s34**2 + 18*s12*s13**2
     &    *s23**2*s34 + 4*s12*s13**3*s23*s34 + s12*s14*s23*s24*s34**2
     &     + 9*s12*s14*s23*s24**2*s34 + 5*s12*s14*s23*s34**3 + 6*s12*
     &    s14*s23**2*s24*s34 + 2*s12*s14*s23**2*s24**2 + 16*s12*s14*
     &    s23**2*s34**2 - 3*s12*s14*s23**3*s34 + 2*s12*s14*s34**4 + 14*
     &    s12*s14**2*s23*s24*s34 - 8*s12*s14**2*s23*s34**2 - 8*s12*
     &    s14**2*s23**2*s24 + 11*s12*s14**2*s23**2*s34 + 8*s12*s14**3*
     &    s23*s34 + 2*s12*s14**3*s23**2 - s12*s23*s24*s34**3 + s12*s23*
     &    s24**2*s34**2 + s12*s23*s24**3*s34 + 2*s12*s23**2*s24*s34**2
     &     + 5*s12*s23**2*s24**2*s34
      wt = wt + 2*s12*s23**2*s34**3 + 5*s12*s23**3*s24*s34 - 2*s12*
     &    s23**3*s34**2 + 2*s12*s23**4*s34 + 18*s12**2*s13*s14*s23*s34
     &     + 9*s12**2*s13*s23*s24*s34 + 17*s12**2*s13*s23*s34**2 + 18*
     &    s12**2*s13*s23**2*s34 + 6*s12**2*s13**2*s23*s34 + 17*s12**2*
     &    s14*s23*s24*s34 - 9*s12**2*s14*s23*s34**2 - 8*s12**2*s14*
     &    s23**2*s34 + 8*s12**2*s14**2*s23*s34 + 8*s12**2*s23*s24*
     &    s34**2 + 3*s12**2*s23*s24**2*s34 - 3*s12**2*s23*s34**3 + 11*
     &    s12**2*s23**2*s24*s34 + 3*s12**2*s23**2*s34**2 + 6*s12**2*
     &    s23**3*s34 + 4*s12**3*s13*s23*s34 + 10*s12**3*s14*s23*s34 + 4
     &    *s12**3*s23*s24*s34 + 12*s12**3*s23*s34**2 + 8*s12**3*s23**2*
     &    s34 + 2*s12**4*s23*s34 + 16*s13*s14*s23*s24*s34**2 + 6*s13*
     &    s14*s23*s24**2*s34 + 11*s13*s14*s23*s34**3 + 6*s13*s14*s23**2
     &    *s24*s34 + 14*s13*s14*s23**2*s34**2 + 8*s13*s14*s23**3*s34 + 
     &    9*s13*s14**2*s23*s24*s34 + 17*s13*s14**2*s23*s34**2 + 17*s13*
     &    s14**2*s23**2*s34 + 4*s13*s14**3*s23*s34 + 3*s13*s23*s24*
     &    s34**3
      wt = wt + 3*s13*s23*s24**2*s34**2 + s13*s23*s24**3*s34 + s13*s23*
     &    s34**4 + 6*s13*s23**2*s24*s34**2 + 3*s13*s23**2*s24**2*s34 + 
     &    3*s13*s23**2*s34**3 + 3*s13*s23**3*s24*s34 + 3*s13*s23**3*
     &    s34**2 + s13*s23**4*s34 + 9*s13**2*s14*s23*s24*s34 + 15*
     &    s13**2*s14*s23*s34**2 + 18*s13**2*s14*s23**2*s34 + 6*s13**2*
     &    s14**2*s23*s34 + 6*s13**2*s23*s24*s34**2 + 3*s13**2*s23*
     &    s24**2*s34 + 3*s13**2*s23*s34**3 + 6*s13**2*s23**2*s24*s34 + 
     &    6*s13**2*s23**2*s34**2 + 3*s13**2*s23**3*s34 + 4*s13**3*s14*
     &    s23*s34 + 3*s13**3*s23*s24*s34 + 4*s13**3*s23*s34**2 + 4*
     &    s13**3*s23**2*s34 + 2*s13**4*s23*s34 + 5*s14*s23*s24*s34**3
     &     + 5*s14*s23*s24**2*s34**2 + s14*s23*s24**3*s34 + 2*s14*s23*
     &    s34**4 + 3*s14*s23**2*s24*s34**2 + 2*s14*s23**2*s24**2*s34 - 
     &    2*s14*s23**2*s34**3 - s14*s23**3*s24*s34 + 2*s14*s23**3*
     &    s34**2 - s14*s23**4*s34 + 12*s14**2*s23*s24*s34**2 + 3*s14**2
     &    *s23*s24**2*s34 + 5*s14**2*s23*s34**3 + 4*s14**2*s23**2*s24*
     &    s34
      wt = wt + 2*s14**2*s23**2*s34**2 + 5*s14**2*s23**3*s34 + 4*s14**3
     &    *s23*s24*s34 + 10*s14**3*s23*s34**2 + 5*s14**3*s23**2*s34 + 2
     &    *s14**4*s23*s34

           D40i=wt/s34**2/s14/s23**2/s12/s1234**2

      return
      end


      function D40a(i1,i3,i4,i5)
* the singular part of D40a
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      s13=y(i1,i3)
      s14=y(i1,i4)
      s34=y(i3,i4)
      s15=y(i1,i5)
      s35=y(i3,i5)
      s45=y(i4,i5)
    
      s134=s13+s14+s34
      s135=s13+s15+s35
      s145=s14+s15+s45
      s345=s34+s35+s45
      s1345=s345+s13+s14+s15

      call DAK(s34,s45,s35,a,b,c)
      s34t1 = a*s13 + b*s14 + c*s15
      s345t = s345
      s45t1 = s1345 - s345t - s34t1
      call DAK(s13,s34,s14,a,b,c)
      s13t5 = a*s15 + b*s35 + c*s45
      s134t = s134
      s34t5 = s1345 - s134t - s13t5

      D40a = A40i(i1,i3,i4,i5)-E40tildi(i1,i3,i5,i4)/2d0
      D40a = D40a
     .     + A30y5map(s14,s13,s34)* S30y5map(s134t,s13t5,s34t5)
     .     + A30y5map(s35,s34,s45)/2d0*
     .   ( S30y5map(s45t1,s34t1,s345t)-R30y5map(s45t1,s34t1,s345t) )
     .     - E30y5map(s45,s35,s34)*Q30y5map(s34t1,s45t1,s345t)
     .     - A30y5map(s14,s13,s34)*
     .   ( E30y5map(s13t5,s134t,s34t5)+Q30y5map(s13t5,s134t,s34t5) )
      return
      end



      function D40c(i1,i3,i4,i5)
* the singular part of D40c
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      s13=y(i1,i3)
      s14=y(i1,i4)
      s34=y(i3,i4)
      s15=y(i1,i5)
      s35=y(i3,i5)
      s45=y(i4,i5)
    
      s134=s13+s14+s34
      s135=s13+s15+s35
      s145=s14+s15+s45
      s345=s34+s35+s45
      s1345=s345+s13+s14+s15

      call DAK(s34,s45,s35,a,b,c)
      s34t1 = a*s13 + b*s14 + c*s15
      s345t = s345
      s45t1 = s1345 - s345t - s34t1
      call DAK(s13,s34,s14,a,b,c)
      s13t5 = a*s15 + b*s35 + c*s45
      s134t = s134
      s34t5 = s1345 - s134t - s13t5
      call DAK(s15,s45,s14,a,b,c)
      s15t3 = a*s13 + b*s35 + c*s34
      s145t = s145
      s45t3 = s1345 - s145t - s15t3


      D40c = Aqppq(i1,i3,i5,i4)/4d0
     .     - E40i(i1,i5,i4,i3) + B40i(i1,i5,i4,i3)
     .     + C40i(i1,i4,i5,i3)
     .  + E30y5map(s34,s35,s45)*Q30y5map(s45t1,s34t1,s345t)
     .  + A30y5map(s14,s13,s34)*E30y5map(s134t,s13t5,s34t5)
     .  + sa30y5map(s14,s45,s15)*Q30y5map(s15t3,s145t,s45t3)
     .  + sa30y5map(s14,s13,s34)*Q30y5map(s13t5,s134t,s34t5)
      return
      end


*
********************************************************      
* from ../ana/E40.sub resp. ./E40.frm
      function E40i(i1,i3,i4,i5)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      s13=y(i1,i3)
      s14=y(i1,i4)
      s34=y(i3,i4)
      s15=y(i1,i5)
      s35=y(i3,i5)
      s45=y(i4,i5)
    
      s134=s13+s14+s34
      s345=s34+s35+s45
      s1345=s345+s13+s14+s15
      
      wt=0d0
      wt = wt
     &  + 4*s13*s14*s34**(-1)*s134*s35 - 4*s13*s14*s34**(-1)*s134*
     &    s35**2*s345**(-1) + s13*s14*s34*s134*s15**(-1)*s35*s45**(-1)
     &     + 2*s13*s14*s34*s134*s15**(-1)*s45**(-1)*s345 - s13*s14*s34*
     &    s134*s15**(-1) + 2*s13*s14*s34*s134*s35*s45**(-1)*s345**(-1)
     &     - s13*s14*s34*s15*s45**(-1) + s13*s14*s34*s35*s45**(-1) + 
     &    s13*s14*s34 + s13*s14*s134*s15**(-1)*s35*s45**(-1)*s345 + s13
     &    *s14*s134*s15**(-1)*s345 - s13*s14**2*s34*s45**(-1) + s13*
     &    s14**2*s134*s15**(-1) + 8*s13*s34**(-1)*s134*s15*s35 - 4*s13*
     &    s34**(-1)*s134*s15*s35**2*s345**(-1) - 4*s13*s34**(-1)*s134*
     &    s15*s345 + 4*s13*s34**(-1)*s134*s35*s345 - 4*s13*s34**(-1)*
     &    s134*s35**2 - 4*s13*s34**(-1)*s134*s45*s345 + s13*s34*s134*
     &    s15**(-1)*s345 + 2*s13*s34*s134*s15*s35*s45**(-1)*s345**(-1)
     &     - 2*s13*s34*s134*s15*s45**(-1) + 2*s13*s34*s134*s35*
     &    s45**(-1) - 2*s13*s34*s134*s45**(-1)*s345 - s13*s34*s15**(-1)
     &    *s45*s345
      wt = wt + s13*s34*s15*s35*s45**(-1) - s13*s34*s15*s45**(-1)*s345
     &     - 3*s13*s34*s15 - 3*s13*s34*s345 + 3*s13*s134*s15**(-1)*s35*
     &    s345 + s13*s134*s15**(-1)*s45*s345 + 6*s13*s134*s15 + 2*s13*
     &    s134*s35 + 3*s13*s134*s345 + s13**2*s14*s34*s134*s15**(-1)*
     &    s45**(-1) + s13**2*s14*s134*s15**(-1)*s45**(-1)*s345 + s13**2
     &    *s14*s134*s15**(-1) + 4*s13**2*s34**(-1)*s134*s35 - 2*s13**2*
     &    s34**(-1)*s134*s35**2*s345**(-1) - 2*s13**2*s34**(-1)*s134*
     &    s345 + s13**2*s34*s134*s35*s45**(-1)*s345**(-1) - s13**2*s34*
     &    s134*s45**(-1) - s13**2*s34 + s13**2*s134*s15**(-1)*s35 + 2*
     &    s13**2*s134*s15**(-1)*s345 + 4*s13**2*s134 + s13**3*s134*
     &    s15**(-1) - 4*s14*s34**(-1)*s134*s15*s35**2*s345**(-1) + 4*
     &    s14*s34**(-1)*s134*s15*s345 + 4*s14*s34**(-1)*s134*s35*s345
     &     - 4*s14*s34**(-1)*s134*s35**2 + 4*s14*s34**(-1)*s134*s45*
     &    s345 + 8*s14*s34**(-1)*s15*s45*s345 - 4*s14*s34**(-1)*s15**2*
     &    s35 + 4*s14*s34**(-1)*s15**2*s345 + 4*s14*s34**(-1)*s35*s45*
     &    s345
      wt = wt + 4*s14*s34**(-1)*s45**2*s345 + s14*s34*s134*s15**(-1)*
     &    s35*s45**(-1)*s345 + 2*s14*s34*s134*s15**(-1)*s345 + 2*s14*
     &    s34*s134*s15*s35*s45**(-1)*s345**(-1) + 3*s14*s34*s134*s15*
     &    s45**(-1) + s14*s34*s134*s35*s45**(-1) + 2*s14*s34*s134*
     &    s45**(-1)*s345 - s14*s34*s134 + s14*s34*s15**(-1)*s35*s345 + 
     &    2*s14*s34*s15**(-1)*s45*s345 + s14*s34*s15*s45**(-1)*s345 + 4
     &    *s14*s34*s15 + 3*s14*s34*s15**2*s45**(-1) + 6*s14*s34*s345 - 
     &    4*s14*s134**(-1)*s15*s35*s345 - 4*s14*s134**(-1)*s15*s45*s345
     &     - 2*s14*s134**(-1)*s15**2*s345 - 4*s14*s134**(-1)*s35*s45*
     &    s345 - 2*s14*s134**(-1)*s35**2*s345 - 2*s14*s134**(-1)*s45**2
     &    *s345 - s14*s134*s15**(-1)*s35*s345 + s14*s134*s15**(-1)*s45*
     &    s345 - 4*s14*s134*s35 + 2*s14*s134*s345 - s14*s15**(-1)*
     &    s35**2*s345 + s14*s15**(-1)*s45**2*s345 - s14*s15*s35*
     &    s45**(-1)*s345 - 2*s14*s15*s35 - s14*s15*s345 - s14*s15**2*
     &    s45**(-1)*s345 - 7*s14*s35*s345 + s14*s45*s345 - 4*s14**2*
     &    s34**(-1)*s134**(-1)*s15*s35*s345
      wt = wt - 4*s14**2*s34**(-1)*s134**(-1)*s15*s45*s345 - 2*s14**2*
     &    s34**(-1)*s134**(-1)*s15**2*s345 - 4*s14**2*s34**(-1)*
     &    s134**(-1)*s35*s45*s345 - 2*s14**2*s34**(-1)*s134**(-1)*
     &    s35**2*s345 - 2*s14**2*s34**(-1)*s134**(-1)*s45**2*s345 - 2*
     &    s14**2*s34**(-1)*s134*s35**2*s345**(-1) - 4*s14**2*s34**(-1)*
     &    s15*s345 - 4*s14**2*s34**(-1)*s35*s345 - 4*s14**2*s34**(-1)*
     &    s45*s345 + 2*s14**2*s34*s134*s15**(-1)*s45**(-1)*s345 + 
     &    s14**2*s34*s134*s35*s45**(-1)*s345**(-1) + 4*s14**2*s34*s134*
     &    s45**(-1) + 3*s14**2*s34*s15*s45**(-1) - s14**2*s34*s45**(-1)
     &    *s345 - s14**2*s34 - s14**2*s134*s15**(-1)*s35 + 4*s14**2*
     &    s134*s15**(-1)*s345 + 6*s14**2*s134 + 2*s14**2*s15**(-1)*s35*
     &    s345 + 2*s14**2*s15**(-1)*s45*s345 - 2*s14**2*s15*s45**(-1)*
     &    s345 + 8*s14**2*s15 - s14**2*s35*s45**(-1)*s345 + 7*s14**2*
     &    s345 + s14**3*s34*s134*s15**(-1)*s45**(-1) + s14**3*s34*
     &    s45**(-1) + s14**3*s134*s15**(-1)*s45**(-1)*s345 + s14**3*
     &    s134*s15**(-1)
      wt = wt - 2*s14**3*s45**(-1)*s345 + 4*s34**(-1)*s134*s15*s35*s345
     &     - 4*s34**(-1)*s134*s15*s35**2 - 4*s34**(-1)*s134*s15*s45*
     &    s345 + 4*s34**(-1)*s134*s15**2*s35 - 2*s34**(-1)*s134*s15**2*
     &    s35**2*s345**(-1) - 2*s34**(-1)*s134*s15**2*s345 - 2*
     &    s34**(-1)*s134*s45**2*s345 - 2*s34*s134**(-1)*s15*s35*s345 - 
     &    2*s34*s134**(-1)*s15*s45*s345 - s34*s134**(-1)*s15**2*s345 - 
     &    2*s34*s134**(-1)*s35*s45*s345 - s34*s134**(-1)*s35**2*s345 - 
     &    s34*s134**(-1)*s45**2*s345 + s34*s134*s15**(-1)*s35*s345 + 
     &    s34*s134*s15**(-1)*s45*s345 + s34*s134*s15*s35*s45**(-1) + 
     &    s34*s134*s15**2*s35*s45**(-1)*s345**(-1) + 2*s34*s134*s345 - 
     &    s34*s15**(-1)*s35*s45*s345 + s34*s15**(-1)*s45**2*s345 + s34*
     &    s15**2*s45**(-1)*s345 - 3*s34*s15**2 + s34*s15**3*s45**(-1)
     &     - 3*s34*s35*s345 + 2*s34*s45*s345 - s34**2*s134*s45**(-1)*
     &    s345 + s134*s15**(-1)*s35*s45*s345 + s134*s15**(-1)*s35**2*
     &    s345 + 6*s134*s15*s345 + 5*s134*s15**2 + 6*s134*s35*s345 + 
     &    s134*s45*s345
      wt = wt + s15*s35*s345 + 2*s15*s35**2 + 7*s15*s45*s345 - 2*s15**2
     &    *s35 + 6*s15**2*s345 + 2*s15**3 + 2*s35*s45*s345 + s35**2*
     &    s345 + 3*s45**2*s345

               
      E40i=wt/s1345**2/s134/s345/s34

      return
      end

************************************************************************
      function E40G(i1,i3,i4,i5)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      s13=y(i1,i3)
      s14=y(i1,i4)
      s34=y(i3,i4)
      s15=y(i1,i5)
      s35=y(i3,i5)
      s45=y(i4,i5)
    
      s134=s13+s14+s34
      s345=s34+s35+s45
      s1345=s345+s13+s14+s15

      call DAK(s34,s45,s35,a,b,c)
      s34t1 = a*s13 + b*s14 + c*s15
      s345t = s345
      s45t1 = s1345 - s345t - s34t1


      E40G= B40i(i1,i3,i4,i5)
      E40G = E40G 
     .    + E30y5map(s35,s45,s34)*Q30y5map(s34t1,s45t1,s345t)
      return
      end

***********************************************************************
* small e40tilde from (6.50)
      function se40tilde(i1,i3,i4,i5)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      s15=y(i1,i5)
      s13=y(i1,i3)
      s35=y(i3,i5)
      s14=y(i1,i4)
      s45=y(i4,i5)
      s34=y(i3,i4)
      s345=s34+s35+s45
      s1345=s345+s13+s14+s15
      
      wt=1/s35/s45*(2*s13*s34+2*s13*s15+2*s13**2+s34*s15+s15**2)
     # + s35/s45/s345**2*(2*s13*s14+2*s13*s15+s13**2
     # + 2*s14*s15+s14**2+s15**2)
     # + 1/s45/s345*(-2*s13*s14-4*s13*s15+s13*s35
     # - 2*s13**2-2*s14*s15+s14*s35+s15*s35-2*s15**2)
       
       se40tilde=wt/s1345**2
       
      return
      end
*************************
* same as function E40tilde, but depending on i1,..,i4 
      function E40tildi(i1,i3,i4,i5)
      implicit real*8(a-h,o-z)
*      
      E40tildi= se40tilde(i1,i3,i4,i5)+se40tilde(i1,i4,i3,i5)
    
      return
      end
*
*******************************************************************
c one-loop single unresolved subtraction term 
c (9.78) and (9.79) combined
c ---------------------------------------------------------------
      function VS1bc1oN2(i1,i2,i3,i4,wtplot)
      implicit real*8(a-h,o-z)
      parameter(pi=3.141592653589793238d0)
      common /s3/s12,s13,s23
      common /plots/plot
      common /yij4/y(4,4)
      logical plot 

      y12=y(i1,i2)
      y13=y(i1,i3)
      y14=y(i1,i4)
      y23=y(i2,i3)
      y24=y(i2,i4)
      y34=y(i3,i4)

      wt=0d0
* 
* 1-3-2 antenna
*
      call pmap4to3(i1,i3,i2,i4,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then

	  ee2=19d0/4d0
	  ff2=-4d0
c s12 = y123
           wtsub = var*( 
     .	   tilda31(y12,y13,y23)*T(s12,s13,s23) 
     .    + A30(i1,i3,i2)*
     .     (tilda31(s12,s13,s23)+ff2*T(s12,s13,s23))    
     .    + A30(i1,i3,i2)*ee2*T(s12,s13,s23) )       ! (9.79) 
 
           if(plot)then
             call bino(1,wtplot*wtsub,4)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* 1-4-2 antenna
*
      call pmap4to3(i1,i4,i2,i3,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then

	  ee2=19d0/4d0
	  ff2=-4d0

          wtsub = var*( 
     .	   tilda31(y12,y14,y24)*T(s12,s13,s23) 
     .    + A30(i1,i4,i2)*
     .     (tilda31(s12,s13,s23)+ff2*T(s12,s13,s23))    
     .    + A30(i1,i4,i2)*ee2*T(s12,s13,s23) )      
 
           if(plot)then
             call bino(1,wtplot*wtsub,4)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif

      VS1bc1oN2 = wt
c      

      return
      end
*
************************************************************************
* function for NF^2 part, sig3s
      function VS1bcNF2(i1,i2,i3,i4,wtplot)
      implicit real*8(a-h,o-z)
      parameter(pi=3.141592653589793238d0)
      common /s3/s12,s13,s23
      common /yij4/y(4,4)
      common /plots/plot
      logical plot 

      y12=y(i1,i2)
      y13=y(i1,i3)
      y14=y(i1,i4)
      y23=y(i2,i3)
      y24=y(i2,i4)
      y34=y(i3,i4)

      wt=0d0
      y134=y13+y14+y34
      y234=y23+y24+y34
      
      betaf=-1d0/3d0    
*
* 1-3-4 antenna
*
      call pmap4to3(i1,i3,i4,i2,1,3,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
          ee5=-10d0/9d0+2d0/3d0*dlog(y34/y134) 
	  E31hat=ee5*E30(i1,i3,i4)
          A31hat=0.d0
           wtsub = var* 
     .	  ( (E31hat-2d0*betaf*dlog(y134)*
     .       E30(i1,i3,i4))*T(s12,s13,s23) 
     .     + E30(i1,i3,i4)*A31hat )     
           if(plot)then
             call bino(1,wtplot*wtsub,4)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif
*
* 3-4-2 antenna
*
      call pmap4to3(i3,i4,i2,i1,3,2,1)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
	
          ee5=-10d0/9d0+2d0/3d0*dlog(y34/y234) 
 	  E31hat=ee5*E30(i2,i3,i4)
          A31hat=0.d0
     
           wtsub = var* 
     .	  ( (E31hat-2d0*betaf*dlog(y234)*
     .       E30(i2,i3,i4))*T(s12,s13,s23) 
     .     + E30(i2,i3,i4)*A31hat )
         
           if(plot)then
             call bino(1,wtplot*wtsub,4)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif

      VS1bcNF2 = wt

      return
      end
*****************************************************************
* B50,a,b,ds for NF*N part of sig3ds
****************************************************************
      function B50ads(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      common /s3/s12,s13,s23
      common /sa3/u12,u13,u23
      common /sb3/w12,w13,w23
      common /sc3/x12,x13,x23
      common /s4/z12,z13,z14,z23,z24,z34
      common /plots/plot
      logical plot 
        
      wt=0d0

      y12=y(i1,i2)
      y13=y(i1,i3)
      y14=y(i1,i4)
      y15=y(i1,i5)
      y23=y(i2,i3)
      y24=y(i2,i4)
      y25=y(i2,i5)
      y34=y(i3,i4)
      y35=y(i3,i5)
      y45=y(i4,i5)

      rinvmin = dmin1(y15,y25,y35,y45)
      qinvmin3 = dmin1(y13,y23,y35)
      qinvmin4 = dmin1(y14,y24,y45)


* relative factor 4 (program=4*(8.2)) has to be included 
*    
* 1-3-4-5 
*
* distinguish 3-4 and 4-5 unresolved in pmap5to3 for E40
* type A is proportional to 1/s15 or 1/s45, but NOT 1/s134
* in pmap5to3(1,2,3,4,5) 2 and 3 are unresolved, 1,4 are radiators
*
* term (e) in (8.2), part I

      EG = E40G(i1,i3,i4,i5)
      EA = E40i(i1,i3,i4,i5) - EG
      call pmap5to3(i1,i5,i4,i3,i2,1,3,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
        wtsub = EA
     #         *A30y5map(s12,s13,s23)*var*4d0
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
	endif 
* subtraction term for (fake) singularities of E40 antenna
c 5 unresolved, 1,4 radiators
* term (f) in (8.2)
      call pmap5to4to3C(i1,i5,i4,i3,i2,1,3,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
       wtsub = -A30y5(i1,i5,i4)*E30y5map(w12,w13,w23)  
     #         *A30y5map(x12,x13,x23)*var*4d0
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
	endif 
c	
c now type G ~1/s34
* term (e) in (8.2), part II		  
      call pmap5to3(i5,i3,i4,i1,i2,1,3,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
        wtsub = EG
     #         *A30y5map(s12,s13,s23)*var*4d0
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
	endif  
!
* term (g) in (8.2), part of split D30 where	
c 3||4 (3,5 rad), then 45tilde unres, 1 and 34tilde radiator	  
      call pmap5to4to3D(i5,i4,i3,i1,i2,1,3,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
! w13=s1(45tilde), w23=s345, w12=s1(34tilde) 
       wtsub = -G30y5(i5,i4,i3)*sd30y5map(w12,w13,w23)  
     #         *A30y5map(x12,x13,x23)*var*4d0
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
	endif
!	      
* term (g) in (8.2), part of split D30 where	
c 3||4 (3,5 rad), then  34tilde unres, 1 and 45tilde radiator	  
      call pmap5to4to3C(i5,i4,i3,i1,i2,3,1,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
! w23=s1(34tilde), w13=s345, w12=s1(45tilde)	
       wtsub = -G30y5(i5,i4,i3)
     #         *sd30y5map(w12,w23,w13)  
     #         *A30y5map(x12,x13,x23)*var*4d0

           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
	endif   
      B50ads = wt

      return
      end
******************************************************************
c B50bds: exchange 1<->2 and 3<->4 with respect to B50ads
c => B50bds is not needed
*****************************************************************
* B50,c/d/e,ds for NF/N part of sig3ds
****************************************************************
      function B50cds(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      common /s3/s12,s13,s23
      common /sa3/u12,u13,u23
      common /sb3/w12,w13,w23
      common /sc3/x12,x13,x23
      common /plots/plot
      logical plot 
            
      wt=0d0
      
      y12=y(i1,i2)
      y13=y(i1,i3)
      y23=y(i2,i3)
      y14=y(i1,i4)
      y24=y(i2,i4)
      y34=y(i3,i4)
      y15=y(i1,i5)
      y25=y(i2,i5)
      y35=y(i3,i5)
      y45=y(i4,i5)
      
* (9.2) * (-4) as for sig4s case (see B50c,d,s in aversubnew.f )
* B40i is symmetric under 1<->2 and 3<->4
* 1-3-4 
*
* term (d) in (9.2)
      call pmap5to3(i1,i3,i4,i2,i5,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
        wtsub = B40i(i1,i3,i4,i2)*2d0
     #         *A30y5map(s12,s13,s23)*var
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
	endif   
* subtraction term for (fake) singularities of B40i antenna
* term (e) in 9.2
      call pmap5to4to3C(i1,i3,i4,i2,i5,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
       wtsub = -E30y5(i1,i3,i4)*A30y5map(w12,w13,w23)  
     #         *A30y5map(x12,x13,x23)*var
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
	endif   
* 1<->2 , 3<->4
      call pmap5to4to3C(i2,i4,i3,i1,i5,1,2,3)
      ss34=y34
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
       wtsub = -E30y5(i2,i3,i4)*A30y5map(w12,w13,w23)  
     #         *A30y5map(x12,x13,x23)*var
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
	endif 
*	
*** exchange 3 <-> 4 explicitly ****
*	  
* 1-4-3 
*
* term (d) in (9.2)
      call pmap5to3(i1,i4,i3,i2,i5,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
       wtsub = B40i(i1,i4,i3,i2)
     #         *A30y5map(s12,s13,s23)*var*2d0
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
	endif  
* subtraction term for (fake) singularities of B40i antenna
* term (e) in 9.2
      call pmap5to4to3C(i1,i4,i3,i2,i5,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
       wtsub = -E30y5(i1,i4,i3)*A30y5map(w12,w13,w23)  
     #         *A30y5map(x12,x13,x23)*var
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
	endif   
* 1<->2   
      call pmap5to4to3C(i2,i3,i4,i1,i5,1,2,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
       wtsub = -E30y5(i2,i4,i3)*A30y5map(w12,w13,w23)  
     #         *A30y5map(x12,x13,x23)*var
      trys4=-E30y5(i2,i4,i3)*A30y5map(w12,w13,w23)
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
	endif 
  111   continue
  
      B50cds = wt

      return
      end
************************************************************************
      function B50dds(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      common /s3/s12,s13,s23
      common /sa3/u12,u13,u23
      common /sb3/w12,w13,w23
      common /sc3/x12,x13,x23
      common /plots/plot
      logical plot 
            
      wt=0d0
*      
* 1-3-5 
*
* term (f) in (9.2)
      call pmap5to3(i1,i3,i5,i4,i2,1,3,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
       wtsub = E40tildi(i1,i3,i4,i5)
     #         *A30y5map(s12,s13,s23)*var
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
	   wto=wtsub
	endif 
* subtraction term for (fake) singularities of E40til antenna
* term (g) in (9.2)
      call pmap5to4to3D(i3,i5,i4,i1,i2,1,3,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
       wtsub = -A30y5(i3,i5,i4)*E30y5map(w13,w12,w23)  
     #         *A30y5map(x12,x13,x23)*var
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
	   wts=wtsub
	endif  
* 1<->2   
*
* term (f) in (9.2)
      call pmap5to3(i2,i3,i5,i4,i1,1,3,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
       wtsub = E40tildi(i2,i3,i4,i5)
     #         *A30y5map(s12,s13,s23)*var
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
	   wto=wto+wtsub
	endif   
* subtraction term for (fake) singularities of E40til antenna
* term (g) in (9.2)
      call pmap5to4to3D(i3,i5,i4,i2,i1,1,3,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
       wtsub = -A30y5(i3,i5,i4)*E30y5map(w13,w12,w23)  
     #         *A30y5map(x12,x13,x23)*var
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
             wt=wt+wtsub
	     wts=wts+wtsub
	endif   
*
c  exchange 3<->4  included explicitly
*
      call pmap5to3(i1,i4,i5,i3,i2,1,3,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
       wtsub = E40tildi(i1,i4,i3,i5)
     #         *A30y5map(s12,s13,s23)*var
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
	   wto=wto+wtsub
	endif 
* subtraction term for (fake) singularities of E40til antenna
      call pmap5to4to3D(i4,i5,i3,i1,i2,1,3,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
       wtsub = -A30y5(i4,i5,i3)*E30y5map(w13,w12,w23)  
     #         *A30y5map(x12,x13,x23)*var
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
	   wts=wts+wtsub
	endif  
* 1<->2   
*
      call pmap5to3(i2,i4,i5,i3,i1,1,3,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
       wtsub = E40tildi(i2,i4,i3,i5)
     #         *A30y5map(s12,s13,s23)*var
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
	   wto=wto+wtsub
	endif   
* subtraction term for (fake) singularities of E40til antenna
      call pmap5to4to3D(i4,i5,i3,i2,i1,1,3,2)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
       wtsub = -A30y5(i4,i5,i3)*E30y5map(w13,w12,w23)  
     #         *A30y5map(x12,x13,x23)*var
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
	endif   

 111   continue

      B50dds = wt

      return
      end

************************************************************************
      function B50eds(i1,i2,i3,i4,i5,wtplot)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      common /s3/s12,s13,s23
      common /sa3/yij,yik,yjk
      common /sb3/wKm,wKl,wlm
      common /sc3/x12,x13,x23
      common /plots/plot
      logical plot 
      common /pcut/ppar(4,5) 
            
      wt=0d0
*
* 1-4-3 
* term (h) in (9.2)
      call pmap5to4to3K(i3,i4,i1,i5,i2,1,2,3)
*     i_l's in position 2 and 4 are unresolved 
*     i in position 3 is  shared  radiator
*     i4=j in (9.2)     
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
*     l=i5,m=i2	
       wtsub = -E30y5(i1,i4,i3)*A30y5map(wKm,wKl,wlm)
     #         *A30y5map(x12,x13,x23)*var
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
	endif   
* 3-4-2   
*
      call pmap5to4to3K(i3,i4,i2,i5,i1,2,1,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
       wtsub = -E30y5(i2,i4,i3)*A30y5map(wKm,wKl,wlm)
     #         *A30y5map(x12,x13,x23)*var
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
	endif   
*
* *******exchange 3<->4 **********	
* 1-3-4 
*
      call pmap5to4to3K(i4,i3,i1,i5,i2,1,2,3)
*     i_l's in position 2 and 4 are unresolved 
*     i4=j in (9.2)     
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
*     l=i5,m=i2	
       wtsub = -E30y5(i1,i3,i4)*A30y5map(wKm,wKl,wlm)
     #         *A30y5map(x12,x13,x23)*var
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
	endif   
* 2-3-4   
*
      call pmap5to4to3K(i4,i3,i2,i5,i1,2,1,3)
      call ecuts(3,var,ipass)
        if(ipass.eq.1)then
       wtsub = -E30y5(i2,i3,i4)*A30y5map(wKm,wKl,wlm)
     #         *A30y5map(x12,x13,x23)*var
           if(plot)then
             call bino(1,wtplot*wtsub,5)
           else
             call distrib(wtdis)
             wtsub = wtsub/wtdis
           endif
           wt=wt+wtsub
        endif   

      B50eds = wt
      return
      end

************************************************************************
* antenna functions with 5->4,5->3 momentum maps
* (same as in aversubnew.f for 4->3 except for 
* different common block yij5 instead of yij4)
c---------------------------------------------------------
c three-parton tree level
c---------------------------------------------------------
c quark-antiquark antennae
c 
      function A30y5(ia,iu,ib)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      yau=y(ia,iu)
      yub=y(iu,ib)
      yab=y(ia,ib)
      yaub=yau+yub+yab
      A30y5=1d0/yaub 
     .     *(yau/yub+yub/yau+2d0*yab*yaub/yau/yub) 
      return
      end
**********************************************************
c A30(ia,iu,ib)=sa30(ia,iu,ib)+sa30(ib,iu,ia) (5.9)
      function sa30y5(ia,iu,ib)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      yau=y(ia,iu)
      yub=y(iu,ib)
      yab=y(ia,ib)
      yaub=yau+yub+yab
      sa30y5=1d0/yaub 
     .     *( yub/yau+2d0*yab*yaub/yau/(yau+yub) ) 
      return
      end
**********************************************************
c quark-gluon antennae
c q-g-g:
c D30(1,3,4)=sd30(1,3,4)+sd30(1,4,3) (6.12)
      function sd30y5(ia,iu,ib)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      yau=y(ia,iu)
      yub=y(iu,ib)
      yab=y(ia,ib)
      yaub=yau+yab+yub
      sd30y5=1d0/yaub**2*( 2d0*yaub**2*yab/yau/yub
     .               + (yab*yub+yub**2)/yau
     .               +  yau*yab/yub+5d0/2d0*yaub+yub/2d0 )
      return
      end
*******************
c if dependence on invariants of pmap is needed:
      function sd30y5map(y14,y13,y34)
      implicit real*8(a-h,o-z)
      common /tcuts/ymin,y0
      y134=y13+y14+y34
      sd30y5map=1d0/y134**2*( 2d0*y134**2*y14/y13/y34
     &               + (y14*y34+y34**2)/y13
     &               +  y13*y14/y34+5d0/2d0*y134+y34/2d0 )
c      if (y13.lt.y0.or.y14.lt.y0.or.y34.lt.y0) sd30y5map = 0d0
      return
      end
************************************************************
      function D30y5map(s14,s13,s34)
      implicit real*8(a-h,o-z)
      common /tcuts/ymin,y0
      D30y5map=sd30y5map(s14,s13,s34)+sd30y5map(s13,s14,s34)
      return
      end
*******************
c g-g-q: corresponds to old Aggq, here just reverse arguments of d30
*******************
c x-q-qbar: (6.14)
      function E30y5(i1,i3,i4)
      implicit real*8(a-h,o-z)
      common /tcuts/ymin,y0
      common /yij5/y(5,5)
      y13=y(i1,i3)
      y34=y(i3,i4)
      y14=y(i1,i4)
      y134=y13+y14+y34
      E30y5=1d0/y134**2*( (y13**2+y14**2)/y34+y13+y14 )
      return
      end
************************************************************
c if dependence on invariants of pmap is needed:
      function E30y5map(s13,s14,s34)
      implicit real*8(a-h,o-z)
      common /tcuts/ymin,y0
      s134=s13+s14+s34
      E30y5map=1d0/s134**2*( (s13**2+s14**2)/s34+s13+s14 )
      return
      end
************************************************************
c small sa30(ia,iu,ib) depending on redefined momenta
      function sa30y5map(sab,sau,sub)
      implicit real*8(a-h,o-z)
      common /tcuts/ymin,y0
c
      saub=sab+sau+sub
      sa30y5map=1d0/saub
     .     *( sub/sau+2d0*sab*saub/sau/(sau+sub) ) 
      return
      end
**********************************************************
c A30(ia,iu,ib) depending on invariants instead of i's
c includes proper normalisation, don't use T(w12,..)/x12 any longer
      function A30y5map(sab,sau,sub)
      implicit real*8(a-h,o-z)
      common /tcuts/ymin,y0
c      
      A30y5map=sa30y5map(sab,sau,sub)+sa30y5map(sab,sub,sau)
      return
      end
**********************************************************
c gluon-gluon antennae
c g-g-g:
c F30(1,2,3)=sf30(1,3,2)+sf30(3,2,1)+sf30(2,1,3)  (7.12) 
c 2/3*s123 -> 8/3*s123 corrected 22.6.06
      function sf30y5(ia,iu,ib)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      yau=y(ia,iu)
      yub=y(iu,ib)
      yab=y(ia,ib)
      yaub=yau+yab+yub
      sf30y5=1d0/yaub**2*( 2d0*yaub**2*yab/yau/yub
     .                 + yab*yub/yau
     .                 + yab*yau/yub
     .                 + 8d0/3d0*yaub )
      return
      end
*************************
c g-q-qbar: (7.14)
      function G30y5(ia,iu,ib)
      implicit real*8(a-h,o-z)
      common /yij5/y(5,5)
      yau=y(ia,iu)
      yub=y(iu,ib)
      yab=y(ia,ib)
      yaub=yau+yab+yub
      G30y5=1d0/yaub**2*(yau**2+yab**2)/yub 
      return
      end



      function Q30y5map(y13,y14,y34)
      implicit real*8(a-h,o-z)
      common /tcuts/ymin,y0
* Q30 = d30(1,3,4) - A30(1,3,4)

      y134 = y13+y14+y34
      Q30y5map= 1/y134**2* 
     .          (3d0/2d0*y13 -y13**2/y34 +2d0*y34 +5d0/2d0*y14)
      return
      end


      function R30y5map(y13,y14,y34)
      implicit real*8(a-h,o-z)
      common /tcuts/ymin,y0
* R30 = d30(1,3,4) - A30(1,3,4) - d30(1,4,3) + A30(1,4,3)

      y134 = y13+y14+y34
      R30y5map= Q30y5map(y13,y14,y34) - Q30y5map(y14,y13,y34)
      return
      end

      function S30y5map(y13,y14,y34)
      implicit real*8(a-h,o-z)
      common /tcuts/ymin,y0

      y134 = y13+y14+y34
      S30y5map= 1/y134**2*(5d0*y134-y34) 
      return
      end


      function sant(i1,i2,i3)
      implicit real*8(a-h,o-z)
      dimension pa(1:4),pu(1:4),pb(1:4)
      common /tcuts/ymin,y0
      common/mapmomenta/p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      
      if (i1.gt.10) then
         if (i1.gt.20) then
            do i=1,4
               pa(i) = p3(i,i1-20)
            enddo
         else
            do i=1,4
               pa(i) = p4(i,i1-10)
            enddo
         endif
      else
         do i=1,4
            pa(i) = p5(i,i1)
         enddo
      endif

      if (i2.gt.10) then
         if (i2.gt.20) then
            do i=1,4
               pu(i) = p3(i,i2-20)
            enddo
         else
            do i=1,4
               pu(i) = p4(i,i2-10)
            enddo
         endif
      else
         do i=1,4
            pu(i) = p5(i,i2)
         enddo
      endif

      if (i3.gt.10) then
         if (i3.gt.20) then
            do i=1,4
               pb(i) = p3(i,i3-20)
            enddo
         else
            do i=1,4
               pb(i) = p4(i,i3-10)
            enddo
         endif
      else
         do i=1,4
            pb(i) = p5(i,i3)
         enddo
      endif
      yab = 2d0*dot(pa(1),pb(1))
      yau = 2d0*dot(pa(1),pu(1))
      ybu = 2d0*dot(pb(1),pu(1))
      yaub = yab+yau+ybu

      sant = 2d0*yab/yau/ybu
      return
      end
