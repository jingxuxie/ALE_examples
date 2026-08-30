subroutine kernel_batch(count, inputs, outputs) bind(C)
use iso_c_binding
implicit none
integer(c_int), value :: count
real(c_double), intent(in) :: inputs(10,count)
real(c_double), intent(out) :: outputs(count)
real(8) :: values(10), forward, backward
real(8), external :: A345
integer :: sample
do sample = 1,count
  values = real(inputs(:,sample),8)
  forward = A345(values(1),values(2),values(3),values(4), &
       values(5),values(6),values(7),values(8),values(9),values(10))
  backward = A345(values(1),values(4),values(3),values(2), &
       values(7),values(6),values(5),values(10),values(9),values(8))
  outputs(sample) = real((forward+backward)/2,c_double)
end do
end subroutine
