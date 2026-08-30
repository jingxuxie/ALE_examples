program mapping_driver
  use iso_c_binding, only: c_ptr, c_null_ptr, c_f_pointer, c_loc, c_int, &
       c_int32_t, c_intptr_t, c_size_t, c_long, c_double
  implicit none
  interface
    function memory_map(address, length, protection, flags, descriptor, offset) bind(C, name='mmap') result(mapped)
      import c_ptr, c_size_t, c_int, c_long
      type(c_ptr), value :: address
      integer(c_size_t), value :: length
      integer(c_int), value :: protection, flags, descriptor
      integer(c_long), value :: offset
      type(c_ptr) :: mapped
    end function
    function memory_unmap(address, length) bind(C, name='munmap') result(status)
      import c_ptr, c_size_t, c_int
      type(c_ptr), value :: address
      integer(c_size_t), value :: length
      integer(c_int) :: status
    end function
    function positioned_read(descriptor, buffer, length, offset) bind(C, name='pread') result(received)
      import c_ptr, c_size_t, c_int, c_long
      integer(c_int), value :: descriptor
      type(c_ptr), value :: buffer
      integer(c_size_t), value :: length
      integer(c_long), value :: offset
      integer(c_long) :: received
    end function
  end interface
  integer(c_int), parameter :: shared_populated = 32769_c_int
  integer(c_int32_t), target :: header(4)
  integer(c_int32_t), pointer :: input_labels(:,:), input_slots(:,:)
  integer(c_int32_t) :: labels(5), slots(3)
  integer(c_int32_t) :: count
  integer(c_int) :: status
  integer(c_long) :: received
  integer(c_size_t) :: input_size, output_size
  integer :: event
  type(c_ptr) :: input_pointer, output_pointer
  real(c_double), pointer :: event_momenta(:,:,:), axes(:,:), records(:,:)
  real(c_double) :: momenta(4,5), mapped(4,5), invariants(5,5), mapped_s(3)
  real(c_double) :: saved5(4,5), saved4(4,4), saved3(4,3)
  real(c_double) :: rotation(4,4), inverse(4,4), energy, axis(4)
  common /pmom/ momenta
  common /pcut/ mapped
  common /yij5/ invariants
  common /s3/ mapped_s
  common /mapmomenta/ saved5, saved4, saved3
  received = positioned_read(0_c_int, c_loc(header), 16_c_size_t, 0_c_long)
  if (received /= 16) stop 2
  if (transfer(header(1:2), '12345678') /= 'ERAD3B4'//achar(0)) stop 3
  count = header(3)
  if (count < 1 .or. count > 20000 .or. header(4) /= 0) stop 4
  input_size = 16_c_size_t + 224_c_size_t*count
  output_size = 16_c_size_t + 672_c_size_t*count
  input_pointer = memory_map(c_null_ptr, input_size, 1_c_int, shared_populated, 0_c_int, 0_c_long)
  output_pointer = memory_map(c_null_ptr, output_size, 3_c_int, shared_populated, 1_c_int, 0_c_long)
  if (transfer(input_pointer, 0_c_intptr_t) == -1_c_intptr_t) stop 5
  if (transfer(output_pointer, 0_c_intptr_t) == -1_c_intptr_t) stop 6
  call c_f_pointer(byte_offset(input_pointer, 16_c_size_t), event_momenta, [4,5,count])
  call c_f_pointer(byte_offset(input_pointer, 16_c_size_t + 160_c_size_t*count), input_labels, [5,count])
  call c_f_pointer(byte_offset(input_pointer, 16_c_size_t + 180_c_size_t*count), input_slots, [3,count])
  call c_f_pointer(byte_offset(input_pointer, 16_c_size_t + 192_c_size_t*count), axes, [4,count])
  call c_f_pointer(byte_offset(output_pointer, 16_c_size_t), records, [84,count])
  do event = 1, count
    momenta = event_momenta(:,:,event)
    labels = input_labels(:,event)
    slots = input_slots(:,event)
    axis = axes(:,event)
    mapped = 0.0_c_double
    saved3 = 0.0_c_double
    energy = sum(momenta(4,:))
    call fillinv(5,momenta,invariants)
    invariants = invariants / (energy*energy)
    call pmap5to3(labels(1),labels(2),labels(3),labels(4),labels(5),slots(1),slots(2),slots(3))
    call rotatetoz(axis,rotation)
    call unrotatetoz(axis,inverse)
    records(:,event) = [reshape(invariants,[25]), reshape(mapped(:,1:3),[12]), mapped_s, &
                       reshape(saved3,[12]), reshape(rotation,[16]), reshape(inverse,[16])]
  end do
  status = memory_unmap(input_pointer, input_size)
  if (status /= 0) stop 7
  status = memory_unmap(output_pointer, output_size)
  if (status /= 0) stop 8
contains
  function byte_offset(base, displacement) result(pointer)
    type(c_ptr), intent(in) :: base
    integer(c_size_t), intent(in) :: displacement
    type(c_ptr) :: pointer
    integer(c_intptr_t) :: address
    address = transfer(base, 0_c_intptr_t) + int(displacement, c_intptr_t)
    pointer = transfer(address, c_null_ptr)
  end function
end program
