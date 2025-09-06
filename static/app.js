
function confirmDelete(e, msg){
  if(!confirm(msg || "Are you sure?")){
    e.preventDefault();
  }
}
