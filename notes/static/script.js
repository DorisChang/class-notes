function toggleElement(obj)
{
    var selectedItem = obj.options[obj.selectedIndex].value;
    if(selectedItem == 'Kansas State University'){
        var ksu = document.getElementsByClassName('Kansas State University');
        for(var i = 0, length = ksu.length; i < length; i++) {
           if( ksu[i].style.display == 'none'){
              ksu[i].style.display = '';
           }
        }
        var landlord = document.getElementsByClassName('Landlord');
        for(var i = 0, length = landlord.length; i < length; i++) {
           if( landlord[i].style.display == ''){
              landlord[i].style.display = 'none';
           } 
        }
    } else if(selectedItem == 'Landlord'){
        var landlord = document.getElementsByClassName('Landlord');
        for(var i = 0, length = landlord.length; i < length; i++) {
           if( landlord[i].style.display == 'none'){
              landlord[i].style.display = '';
           } 
        }
        var tenants = document.getElementsByClassName('Tenant');
        for(var i = 0, length = tenants.length; i < length; i++) {
           if( tenants[i].style.display == ''){
              tenants[i].style.display = 'none';
           }
        }
    } else{
        var landlord = document.getElementsByClassName('Landlord');
        for(var i = 0, length = landlord.length; i < length; i++) {
              landlord[i].style.display = '';
        }
        var tenants = document.getElementsByClassName('Tenant');
        for(var i = 0, length = tenants.length; i < length; i++) {
              tenants[i].style.display = '';
        }
    }
}