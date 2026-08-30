      subroutine pmap5to3(i1,i2,i3,i4,i5,j1,j2,j3)
      implicit real*8(a-h,o-z)
      common/yij5/y(5,5)
      common/s3/s12,s13,s23
      common/pmom/p(4,5) 
      common/pcut/ppar(4,5)
      common/mapmomenta/p5(1:4,1:5),p4(1:4,1:4),p3(1:4,1:3)
      dimension s(3,3),antenna(4,4),mapped(4,2)
      real*8 mapped

      y12=y(i1,i2)
      y13=y(i1,i3)
      y14=y(i1,i4)
      y23=y(i2,i3)
      y24=y(i2,i4)
      y34=y(i3,i4)

      energy=sum(p(4,:))
      antenna(:,1)=p(:,i1)
      antenna(:,2)=p(:,i2)
      antenna(:,3)=p(:,i3)
      antenna(:,4)=p(:,i4)
      total=y12+y13+y14+y23+y24+y34
      if(total.lt.1d-6) then
         call mapwide(antenna,energy,mapped)
      else
         call mapextended(antenna,energy,mapped)
      endif

      do i=1,4
         ppar(i,j1) = mapped(i,1)
         ppar(i,j2) = mapped(i,2)
         ppar(i,j3) = p(i,i5)
         p3(i,j1) = ppar(i,j1)
         p3(i,j2) = ppar(i,j2)
         p3(i,j3) = ppar(i,j3)
      enddo

      do i=1,3
         do j=i+1,3
            s(i,j)=2d0*(dot(ppar(1,i),ppar(1,j))/energy)/energy
         enddo
      enddo

      s12 = s(1,2)
      s13 = s(1,3)
      s23 = s(2,3)

      return
      end


      subroutine mapextended(input,energy,mapped)
      implicit none
      real*8 input(4,4),energy,mapped(4,2)
      real(10) vectors(4,4),pairs(4,4),total(4),base(4)
      real(10) direction(4),center(4),answer(4),cross(3)
      real(10) spatial,mass,ca,cb,cu,cv,weight1,weight2
      real(10) target,projection,radius,normdir
      real(10) opening
      integer first,second
      vectors=real(input,10)/real(energy,10)
      do first=1,4
         vectors(4,first)=sqrt(sum(vectors(1:3,first)**2))
      enddo
      pairs=0
      do first=1,4
         do second=first+1,4
            spatial=sum(vectors(1:3,first)*vectors(1:3,second))
            if(spatial.gt.0) then
               cross(1)=vectors(2,first)*vectors(3,second)
     .                 -vectors(3,first)*vectors(2,second)
               cross(2)=vectors(3,first)*vectors(1,second)
     .                 -vectors(1,first)*vectors(3,second)
               cross(3)=vectors(1,first)*vectors(2,second)
     .                 -vectors(2,first)*vectors(1,second)
               pairs(first,second)=2*sum(cross**2)/
     .              (vectors(4,first)*vectors(4,second)+spatial)
            else
               pairs(first,second)=2*
     .              (vectors(4,first)*vectors(4,second)-spatial)
            endif
            pairs(second,first)=pairs(first,second)
         enddo
      enddo
      total=sum(vectors,dim=2)
      mass=sum(pairs)/2
      ca=sum(pairs(1,:))/2
      cb=sum(pairs(4,:))/2
      cu=sum(pairs(2,:))/2
      cv=sum(pairs(3,:))/2
      weight1=(pairs(2,4)+pairs(2,3))/
     .        (pairs(1,2)+pairs(2,4)+pairs(2,3))
      weight2=pairs(3,4)/
     .        (pairs(1,3)+pairs(3,4)+pairs(2,3))
      target=mass/2-weight1*cu-weight2*cv
      normdir=sqrt(pairs(1,4)/(ca*cb))
      direction=(vectors(:,1)/ca-vectors(:,4)/cb)/normdir
      opening=pairs(1,4)/(vectors(4,1)*vectors(4,4))
      if(opening.lt.1.0e-8_10) then
         projection=(total(4)*direction(4)
     .             -sum(total(1:3)*direction(1:3)))/mass
         direction=direction-projection*total
         normdir=sqrt(sum(direction(1:3)**2)-direction(4)**2)
         direction=direction/normdir
      endif
      base=weight1*vectors(:,2)+weight2*vectors(:,3)
     .     +(target/cb)*vectors(:,4)
      projection=base(4)*direction(4)
     .           -sum(base(1:3)*direction(1:3))
      center=base+projection*direction
      radius=sqrt(max(0.0_10,center(4)**2-sum(center(1:3)**2)))
      answer=center+radius*direction
      mapped(:,1)=real(answer*real(energy,10),8)
      mapped(:,2)=real((total-answer)*real(energy,10),8)
      end

      subroutine mapwide(input,energy,mapped)
      implicit none
      real*8 input(4,4),energy,mapped(4,2)
      real(16) vectors(4,4),pairs(4,4),total(4),answer(4),cross(3)
      real(16) spatial,mass,weight1,weight2
      real(16) ya1,ya2,y1b,y2b,y12,yab,rho2,rho
      real(16) firstweight,lastweight
      integer first,second
      vectors=real(input,16)/real(energy,16)
      do first=1,4
         vectors(4,first)=sqrt(sum(vectors(1:3,first)**2))
      enddo
      pairs=0
      do first=1,4
         do second=first+1,4
            spatial=sum(vectors(1:3,first)*vectors(1:3,second))
            if(spatial.gt.0) then
               cross(1)=vectors(2,first)*vectors(3,second)
     .                 -vectors(3,first)*vectors(2,second)
               cross(2)=vectors(3,first)*vectors(1,second)
     .                 -vectors(1,first)*vectors(3,second)
               cross(3)=vectors(1,first)*vectors(2,second)
     .                 -vectors(2,first)*vectors(1,second)
               pairs(first,second)=2*sum(cross**2)/
     .              (vectors(4,first)*vectors(4,second)+spatial)
            else
               pairs(first,second)=2*
     .              (vectors(4,first)*vectors(4,second)-spatial)
            endif
            pairs(second,first)=pairs(first,second)
         enddo
      enddo
      total=sum(vectors,dim=2)
      mass=sum(pairs)/2
      ya1=pairs(1,2)/mass
      ya2=pairs(1,3)/mass
      y1b=pairs(2,4)/mass
      y2b=pairs(3,4)/mass
      y12=pairs(2,3)/mass
      yab=pairs(1,4)/mass
      weight1=(y1b+y12)/(ya1+y1b+y12)
      weight2=y2b/(ya2+y2b+y12)
      rho2=1+(weight1-weight2)**2/yab**2*
     .     (yab**2*y12**2+ya1**2*y2b**2+ya2**2*y1b**2
     .     -2*(yab*ya1*y2b*y12+yab*ya2*y1b*y12+ya1*ya2*y1b*y2b))
     .     +((weight1*(1-weight2)+weight2*(1-weight1))
     .     *2*(yab*ya1*y2b+yab*ya2*y1b-yab**2*y12)
     .     +4*weight1*(1-weight1)*yab*ya1*y1b
     .     +4*weight2*(1-weight2)*yab*ya2*y2b)/yab**2
      rho=sqrt(rho2)
      firstweight=((1+rho)-(2*y1b+y12)*weight1
     .           -(2*y2b+y12)*weight2
     .           +(ya1*y2b-ya2*y1b)*(weight1-weight2)/yab)
     .           /(2*(yab+ya1+ya2))
      lastweight=((1-rho)-(2*ya1+y12)*weight1
     .          -(2*ya2+y12)*weight2
     .          -(ya1*y2b-ya2*y1b)*(weight1-weight2)/yab)
     .          /(2*(yab+y1b+y2b))
      answer=firstweight*vectors(:,1)+weight1*vectors(:,2)
     .      +weight2*vectors(:,3)+lastweight*vectors(:,4)
      mapped(:,1)=real(answer*real(energy,16),8)
      mapped(:,2)=real((total-answer)*real(energy,16),8)
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
      rho = sqrt(rho2)
      
      
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
