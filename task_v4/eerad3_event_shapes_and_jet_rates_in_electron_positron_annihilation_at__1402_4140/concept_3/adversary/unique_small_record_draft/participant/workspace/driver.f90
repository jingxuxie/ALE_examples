program mapping_driver
  use iso_fortran_env, only: int32, real64
  implicit none
  type event_record
    real(real64) :: momenta(4,5)
    integer(int32) :: labels(5), slots(3)
    real(real64) :: axis(4)
  end type
  type(event_record), allocatable :: events(:)
  real(real64), allocatable :: records(:,:)
  integer(int32) :: count
  integer :: event, input_unit, output_unit, io_status
  character(len=8) :: magic
  real(real64) :: momenta(4,5), mapped(4,5), invariants(5,5), mapped_s(3)
  real(real64) :: saved5(4,5), saved4(4,4), saved3(4,3)
  real(real64) :: rotation(4,4), inverse(4,4), energy
  common /pmom/ momenta
  common /pcut/ mapped
  common /yij5/ invariants
  common /s3/ mapped_s
  common /mapmomenta/ saved5, saved4, saved3
  open(newunit=input_unit, file='/dev/stdin', access='stream', form='unformatted', &
       action='read', convert='little_endian', iostat=io_status)
  if (io_status /= 0) stop 2
  read(input_unit, iostat=io_status) magic, count
  if (io_status /= 0 .or. magic /= 'ERAD3B2'//achar(0)) stop 3
  if (count < 1 .or. count > 20000) stop 4
  allocate(events(count), records(84,count))
  read(input_unit, iostat=io_status) events
  if (io_status /= 0) stop 5
  close(input_unit)
  do event = 1, count
    momenta = events(event)%momenta
    mapped = 0.0_real64
    saved3 = 0.0_real64
    energy = sum(momenta(4,:))
    call fillinv(5,momenta,invariants)
    invariants = invariants / (energy*energy)
    call pmap5to3(events(event)%labels(1),events(event)%labels(2),events(event)%labels(3), &
                 events(event)%labels(4),events(event)%labels(5),events(event)%slots(1), &
                 events(event)%slots(2),events(event)%slots(3))
    call rotatetoz(events(event)%axis,rotation)
    call unrotatetoz(events(event)%axis,inverse)
    records(:,event) = [reshape(invariants,[25]), reshape(mapped(:,1:3),[12]), mapped_s, &
                       reshape(saved3,[12]), reshape(rotation,[16]), reshape(inverse,[16])]
  end do
  open(newunit=output_unit, file='/dev/stdout', access='stream', form='unformatted', &
       action='write', convert='little_endian', iostat=io_status)
  if (io_status /= 0) stop 6
  write(output_unit) 'ERAD3O2'//achar(0), count, records
  close(output_unit)
end program
