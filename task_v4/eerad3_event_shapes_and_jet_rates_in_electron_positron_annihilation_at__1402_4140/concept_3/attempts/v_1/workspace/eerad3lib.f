      function dot(a,b)
      implicit none
      real*8 dot,a(4),b(4),avec(3),bvec(3),anorm,bnorm
      real*8 nullpair
      integer aexp,bexp,component
      aexp=exponent(maxval(abs(a(1:3))))
      bexp=exponent(maxval(abs(b(1:3))))
      do component=1,3
         avec(component)=scale(a(component),-aexp)
         bvec(component)=scale(b(component),-bexp)
      enddo
      anorm=sqrt(sum(avec**2))
      bnorm=sqrt(sum(bvec**2))
      dot=scale(nullpair(avec,bvec,anorm,bnorm),aexp+bexp)
      end

      function nullpair(avec,bvec,anorm,bnorm)
      implicit none
      real*8 nullpair,avec(3),bvec(3),anorm,bnorm
      real*8 product,cross(3),square,detprod
      product=sum(avec*bvec)
      if(product.lt.0.9d0*anorm*bnorm) then
         nullpair=anorm*bnorm-product
      else
         cross(1)=avec(2)*bvec(3)-avec(3)*bvec(2)
         cross(2)=avec(3)*bvec(1)-avec(1)*bvec(3)
         cross(3)=avec(1)*bvec(2)-avec(2)*bvec(1)
         square=sum(cross**2)
         if(square.lt.1d-6*(anorm*bnorm)**2) then
            cross(1)=detprod(avec(2),bvec(3),avec(3),bvec(2))
            cross(2)=detprod(avec(3),bvec(1),avec(1),bvec(3))
            cross(3)=detprod(avec(1),bvec(2),avec(2),bvec(1))
            square=sum(cross**2)
         endif
         nullpair=square/(anorm*bnorm+product)
      endif
      end

      function detprod(first,second,third,fourth)
      implicit none
      real*8 detprod,first,second,third,fourth,split
      real*8 high1,high2,high3,high4,low1,low2,low3,low4
      real*8 temp,prod1,prod2,error1,error2
      parameter(split=134217729d0)
      temp=split*first
      high1=temp-(temp-first)
      low1=first-high1
      temp=split*second
      high2=temp-(temp-second)
      low2=second-high2
      temp=split*third
      high3=temp-(temp-third)
      low3=third-high3
      temp=split*fourth
      high4=temp-(temp-fourth)
      low4=fourth-high4
      prod1=first*second
      prod2=third*fourth
      error1=((high1*high2-prod1)+high1*low2+low1*high2)
     .       +low1*low2
      error2=((high3*high4-prod2)+high3*low4+low3*high4)
     .       +low3*low4
      detprod=(prod1-prod2)+(error1-error2)
      end
