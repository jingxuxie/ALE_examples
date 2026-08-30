subroutine eerad3_batch(input_pointer, output_pointer, count) bind(C, name='eerad3_batch')
  use iso_c_binding, only: c_ptr, c_null_ptr, c_f_pointer, &
       c_int32_t, c_intptr_t, c_size_t, c_double
  implicit none
  integer(c_int32_t), pointer :: input_labels(:,:), input_slots(:,:)
  integer(c_int32_t) :: labels(5), slots(3)
  integer(c_int32_t), value :: count
  integer :: event
  type(c_ptr), value :: input_pointer, output_pointer
  real(c_double), pointer :: event_momenta(:,:,:), axes(:,:), records(:,:)
  real(c_double) :: momenta(4,5), mapped(4,5), invariants(5,5), mapped_s(3)
  real(c_double) :: saved5(4,5), saved4(4,4), saved3(4,3)
  real(c_double) :: rotation(4,4), inverse(4,4), energy, axis(4)
  common /pmom/ momenta
  common /pcut/ mapped
  common /yij5/ invariants
  common /s3/ mapped_s
  common /mapmomenta/ saved5, saved4, saved3
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
contains
  function byte_offset(base, displacement) result(pointer)
    type(c_ptr), intent(in) :: base
    integer(c_size_t), intent(in) :: displacement
    type(c_ptr) :: pointer
    integer(c_intptr_t) :: address
    address = transfer(base, 0_c_intptr_t) + int(displacement, c_intptr_t)
    pointer = transfer(address, c_null_ptr)
  end function
end subroutine
