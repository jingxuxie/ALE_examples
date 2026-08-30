program mapping_driver
  implicit none
  integer :: count, repeats, event, iteration, particle, component
  integer, allocatable :: labels(:,:), slots(:,:)
  real(8), allocatable :: events(:,:,:), axes(:,:)
  real(8) :: momenta(4,5), mapped(4,5), invariants(5,5), mapped_s(3)
  real(8) :: saved5(4,5), saved4(4,4), saved3(4,3)
  real(8) :: rotation(4,4), inverse(4,4), energy, started, stopped, checksum
  common /pmom/ momenta
  common /pcut/ mapped
  common /yij5/ invariants
  common /s3/ mapped_s
  common /mapmomenta/ saved5, saved4, saved3
  read(*,*) count, repeats
  if (count < 1 .or. count > 4096 .or. repeats < 1 .or. repeats > 1000000) stop 2
  allocate(events(4,5,count), axes(4,count), labels(5,count), slots(3,count))
  do event = 1, count
    read(*,*) events(:,:,event)
    read(*,*) labels(:,event), slots(:,event)
    read(*,*) axes(:,event)
  end do
  checksum = 0d0
  do event = 1, count
    call execute_event(event)
    write(*,'(84(ES26.17E3,1X))') invariants, mapped(:,1:3), mapped_s, saved3, rotation, inverse
  end do
  call cpu_time(started)
  do iteration = 1, repeats
    do event = 1, count
      call execute_event(event)
      checksum = checksum + mapped(1,1) / energy + rotation(1,1)
    end do
  end do
  call cpu_time(stopped)
  write(*,'(A,2(ES26.17E3,1X))') 'TIME ', stopped-started, checksum
contains
  subroutine execute_event(index)
    integer, intent(in) :: index
    momenta = events(:,:,index)
    mapped = 0d0
    saved3 = 0d0
    energy = sum(momenta(4,:))
    call fillinv(5,momenta,invariants)
    invariants = invariants / (energy*energy)
    call pmap5to3(labels(1,index),labels(2,index),labels(3,index),labels(4,index), &
                 labels(5,index),slots(1,index),slots(2,index),slots(3,index))
    call rotatetoz(axes(:,index),rotation)
    call unrotatetoz(axes(:,index),inverse)
  end subroutine
end program
