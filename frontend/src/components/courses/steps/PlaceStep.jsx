import PlaceSearch from "../../places/PlaceSearch";

export default function PlaceStep({gotoNextStep, places, addPlace, removePlace}) {
  
  
  return (
    <div>
      <PlaceSearch onAddPlace={addPlace}/>
      
    </div>
  )
}