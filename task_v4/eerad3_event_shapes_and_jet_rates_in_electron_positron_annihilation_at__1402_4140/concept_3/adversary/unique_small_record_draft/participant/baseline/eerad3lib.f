      function dot(a,b)
      implicit real*8(a-h,o-z)
      dimension a(4),b(4)
      dot=a(4)*b(4)-a(1)*b(1)-a(2)*b(2)-a(3)*b(3)
      return
      end
