program native_driver
  implicit none
  double precision :: ppar(4,5), cutdata(13)
  double precision :: thrust, major, minor, oblate, heavy, light, difference
  double precision :: wide, narrow, total, bdiff, cpar, dpar, y45, y34, y23
  double precision :: fc0, fc1, fc2, fc3, bks0, bks1, bks2, bks3
  integer :: event_count, event_index, parton_index
  common /pcut/ ppar
  common /cuts/ cutdata
  cutdata = 0d0
  read(*,*) event_count
  do event_index = 1, event_count
    do parton_index = 1, 5
      read(*,*) ppar(4,parton_index), ppar(1,parton_index), &
                ppar(2,parton_index), ppar(3,parton_index)
    end do
    call getCD(cpar,dpar,5)
    call getT(thrust,major,minor,oblate,heavy,light,difference, &
              wide,narrow,total,bdiff, &
              fc0,fc1,fc2,fc3,bks0,bks1,bks2,bks3,5)
    call getjet(y45,y34,y23,5,2,1)
    write(*,'(8(ES25.16E3,1X))') 1d0-thrust,cpar,heavy,total,wide,y23,y34,y45
  end do
end program native_driver

double precision function dot(first,second)
  implicit none
  double precision :: first(4), second(4)
  dot = first(4)*second(4) - sum(first(1:3)*second(1:3))
end function dot
