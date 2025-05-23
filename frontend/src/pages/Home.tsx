import Map from '../components/Map';

const Home = () => {
  return (
    <div style={{
      width: '100vw',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center'
    }}>
      <h2 style={{ color: '#fff', marginBottom: '2rem' }}>Welcome! You are logged in.</h2>
      <Map />
    </div>
  );
};

export default Home; 